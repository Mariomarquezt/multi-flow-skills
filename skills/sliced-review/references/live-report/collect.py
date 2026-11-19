#!/usr/bin/env python3
"""Print one JSON snapshot of every sliced-review lane and triage judge, for the live report.

Runs on the host where lane.sh runs (usually the laptop). Reads the kits root (env SR_KITS,
default ~/work/sr-kits): lanes.tsv, apps.txt / apps2.txt (or env SR_APPS="a,b"), and per app
out/<lane>/<slice>.md, out/<lane>/<slice>.claimed, ledger*.tsv, plus tri-<app>/ triage kits.
Python 3 stdlib + ../templates/usage.py. Prints JSON on stdout; never writes."""
import csv, glob, json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "templates"))
import usage as U   # tools/usage.py: normalized tokens + API-equivalent price (prices.json -> runner table -> OpenRouter)

K = os.path.expanduser(os.environ.get("SR_KITS", "~/work/sr-kits"))
LANES = {}
for l in open(f"{K}/lanes.tsv"):
    p = l.rstrip("\n").split("\t")
    if len(p) >= 3: LANES[p[0]] = {"provider": p[1], "model": p[2]}
apps = [a for a in os.environ.get("SR_APPS", "").split(",") if a] or \
       [a.strip() for f in ("apps.txt", "apps2.txt") if os.path.exists(f"{K}/{f}") for a in open(f"{K}/{f}") if a.strip()]
SEV = re.compile(r"\b(CRITICAL|HIGH|MEDIUM|LOW)\b")

def sev_counts(text):
    c = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for line in text.splitlines():
        head = line.strip()[:90]
        if not head or head.lower().startswith(("total findings", "severity:", "no ")): continue
        m = SEV.search(head)
        if m and re.search(r"(finding|^[-*#\d]|\*\*|^\[|—|:)", head, re.I):
            c[m.group(1)] += 1
    return c

# Claude CLI does not know the 5.5 prices (Haiku 5.5 billed as "unrecognized_model" at a fallback rate),
# so Claude cost is computed from tokens. USD per 1M tokens (set 2026-10-15). Cache write 1.25x in, read 0.1x in.
CLAUDE_PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0), "claude-opus-5-5": (4.0, 20.0)}
def usage_tokens(u):
    g = lambda k: int(m.group(1)) if (m := re.search(rf"\b{k}=(\d+)", u or "")) else 0
    if not u or not re.search(r"\bout=\d+", u): return None
    return {"in": g("in"), "cached": g("cache_read") or g("cached"), "cache_write": g("cache_write"), "out": g("out")}
def usage_cost(u, model=""):
    if (u or "").startswith("claude usage") and model in CLAUDE_PRICE:
        t = usage_tokens(u); pi, po = CLAUDE_PRICE[model]
        return (t["in"] * pi + t["cache_write"] * pi * 1.25 + t["cached"] * pi * 0.1 + t["out"] * po) / 1e6
    m = re.search(r"est_usd=([0-9.]+)", u or "") or re.search(r"cost=\$?([0-9.]+)", u or "")
    return float(m.group(1)) if m else None

def read_ledger(lf):
    """Ledger rows, each with r["_tok"] = normalized tokens (side file tokens-<ledger> first, else the usage column)."""
    side, sp = {}, U.side_path(lf)
    if os.path.exists(sp):
        for t in csv.DictReader(open(sp), delimiter="\t"):
            if t.get("out", "") != "":
                side[(t["slice"], t["lane"], t["ts"])] = U.T(t["in"] or 0, t["cached"] or 0, t["cache_write"] or 0, t["out"] or 0)
    rows = list(csv.DictReader(open(lf), delimiter="\t"))
    for r in rows:
        r["_tok"] = side.get((r.get("slice"), r.get("lane"), r.get("ts"))) or U.from_text(r.get("provider", ""), r.get("usage", ""))
    return rows
def tok_summary(rs):
    """tokens {in, cached, cache_write, out} + api_usd (price x tokens) for ANY lane, free or flat-plan included."""
    toks, usd, priced, unpriced = [], 0.0, 0, set()
    for r in rs:
        t = r.get("_tok")
        if not t or not any(t.values()): continue
        toks.append(t)
        u = U.api_usd(t, r.get("model", ""), r.get("provider", ""))
        if u is None: unpriced.add(r.get("model", ""))
        else: usd += u; priced += 1
    return {"tokens": {k: sum(t[k] for t in toks) for k in ("in", "cached", "cache_write", "out")} if toks else None,
            "tok_runs": len(toks), "api_usd": round(usd, 4) if priced else None, "api_runs": priced,
            "api_unpriced": sorted(unpriced)}

out = {"generated": time.strftime("%Y-%m-%d %H:%M %Z"), "apps": [], "lanes": LANES, "stops": [], "warns": []}
ALIAS = {}
if os.path.exists(f"{K}/alias.tsv"):
    for l in open(f"{K}/alias.tsv"):
        p = l.rstrip("\n").split("\t")
        if len(p) == 2: ALIAS[p[0]] = p[1]
ROUTES = {}
CUR = {}  # folded lane -> the lanes.tsv row it last ran on (its provider and model show on the page)
MOVED = set(l.strip() for l in open(f"{K}/MOVED.txt")) if os.path.exists(f"{K}/MOVED.txt") else set()
out["moved"] = sorted(MOVED)
for f in glob.glob(f"{K}/STOP.lane.*"):
    if os.path.basename(f)[10:] not in MOVED: out["stops"].append(os.path.basename(f)[10:])
for f in glob.glob(f"{K}/WARN.*"): out["warns"].append(os.path.basename(f)[5:])
for app in apps:
    A = f"{K}/{app}"
    ready = os.path.exists(f"{A}/READY") or os.path.exists(f"{A}/queue.txt")  # a kit with a queue is ready
    q = [l.strip() for l in open(f"{A}/queue.txt")] if os.path.exists(f"{A}/queue.txt") else []
    q = [x for x in q if x]
    led = []
    for lf in sorted(glob.glob(f"{A}/ledger*.tsv")):
        led += read_ledger(lf)
    for r in led:  # fold second routes (e.g. argon-dev) into the model's main row
        if r["lane"] in ALIAS:
            CUR[ALIAS[r["lane"]]] = r["lane"]
            ROUTES.setdefault(ALIAS[r["lane"]], set()).add(r["provider"]); r["lane"] = ALIAS[r["lane"]]
        else:
            ROUTES.setdefault(r["lane"], set()).add(r["provider"])
    # a lane running now wins over the ledger: "lane.sh <app> <lane>" in the process list
    try:
        ps = subprocess.run(["pgrep", "-af", f"lane.sh {app} "], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        ps = ""
    for pl in ps.splitlines():
        real = pl.split()[-1]
        if real in LANES:
            CUR[ALIAS.get(real, real)] = real
            ROUTES.setdefault(ALIAS.get(real, real), set()).add(LANES[real]["provider"])
    lanes = {}
    for lane in sorted(set(r["lane"] for r in led) | (set(os.listdir(f"{A}/out")) if os.path.isdir(f"{A}/out") else set())):
        mds = glob.glob(f"{A}/out/{lane}/*.md")
        tot, sev = 0, {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for m in mds:
            t = open(m, errors="ignore").read()
            n = re.findall(r"TOTAL FINDINGS:?\s*\**\s*(\d+)", t)
            tot += int(n[-1]) if n else 0
            for k, v in sev_counts(t).items(): sev[k] += v
        rs = [r for r in led if r["lane"] == lane]
        ok = [int(r["secs"]) for r in rs if r["status"] == "OK"]
        costs = [usage_cost(r.get("usage", ""), r.get("model", "")) for r in rs]
        ts = tok_summary(rs)
        known = [c for c in costs if c is not None]
        fails = {}
        for r in rs:
            if r["status"] != "OK": fails[r["status"]] = fails.get(r["status"], 0) + 1
        lanes[lane] = {
            "done": len(mds), "running": len(glob.glob(f"{A}/out/{lane}/*.claimed")),
            "active": [{"slice": os.path.basename(c)[:-8], "secs": int(time.time() - os.path.getmtime(c))}
                       for c in glob.glob(f"{A}/out/{lane}/*.claimed")],
            "last_ok": max((r["ts"] for r in rs if r["status"] == "OK"), default=""),
            "findings": tot, "sev": sev, "avg_secs": (sum(ok) // len(ok)) if ok else None,
            "total_secs": sum(int(r["secs"]) for r in rs), "fails": fails,
            "cost": round(sum(known), 4) if known else None, "cost_runs": len(known),
            "tokens": ts["tokens"], "tok_runs": ts["tok_runs"], "api_usd": ts["api_usd"], "api_runs": ts["api_runs"],
            "api_unpriced": ts["api_unpriced"], "ok_secs": sum(ok),
            "stopped": (os.path.exists(f"{A}/STOP.{lane}") or lane in out["stops"]) and lane not in MOVED
                       and not any(t == lane and a not in out["stops"] for a, t in ALIAS.items()),
            "mac": lane in MOVED,
        }
    out["apps"].append({"app": app, "ready": ready, "slices": len(q), "lanes": lanes})

# provider quotas readable from the laptop
def sh(cmd, t=40):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception: return ""
out["quota"] = {"cline_pct_used": sh("$RUNNERS_DIR/cline/cline-quota.py --pct 2>/dev/null | tail -1"),
                "cmd_status": sh("python3 $RUNNERS_DIR/cmd/cmd-pool.py status 2>/dev/null | head -8")}
mem = sh("free -m | awk '/Mem:/{print $2, $7}'").split()
out["host"] = {"mem_total_mb": mem[0] if mem else "", "mem_avail_mb": mem[1] if len(mem) > 1 else "",
                 "load": sh("cut -d' ' -f1-3 /proc/loadavg")}

# triage (tri-<app> kits): verdicts parsed from the json block of each triage report
def tri_items(t):
    m = re.findall(r"```json\s*(\[.*?\])\s*```", t, re.S)
    if m:
        try: return json.loads(m[-1])
        except Exception: pass
    # lenient: decode each {"id": ...} object after the last json fence (judges sometimes write broken JSON)
    i = t.rfind("```json")
    if i < 0: return None
    dec, got = json.JSONDecoder(), []
    for mm in re.finditer(r'\{\s*"id"', t[i:]):
        try: got.append(dec.raw_decode(t[i:], mm.start())[0])
        except Exception: pass
    return got or None
TRI = []
for app in apps:
    T = f"{K}/tri-{app}"
    if not os.path.isdir(T): continue
    q = [l.strip() for l in open(f"{A}/queue.txt")] if False else [l.strip() for l in open(f"{K}/{app}/queue.txt") if l.strip()]
    who, trows = {}, []  # who[slice] = every judge lane that finished it (the v2.5 panel has 3)
    for lf in glob.glob(f"{T}/ledger*.tsv"):
        for r in read_ledger(lf):
            trows.append(r)
            if r["status"] == "OK": who.setdefault(r["slice"], set()).add(r["lane"])
    sl = []
    for s in q:
        f = f"{T}/out/triage/{s}.md"
        st = "done" if os.path.exists(f) else ("running" if os.path.exists(f"{T}/out/triage/{s}.claimed") else
             ("queued" if os.path.exists(f"{T}/inputs/{s}.md") else "waiting"))
        items = tri_items(open(f, errors="ignore").read()) if st == "done" else None
        if st == "done" and items is None: st = "bad-json"
        # 10-17: fold DELTA triage (<s>-dN.md) in. A repeat keeps its base id -> add the new found_by lanes to the
        # base item; a new defect (id prefix <s>-dN-) is appended. So per-lane counts and bug totals both stay right.
        if st == "done" and items is not None:
            byid = {str(i.get("id")): i for i in items if isinstance(i, dict)}
            for df in sorted(glob.glob(f"{T}/out/triage/{s}-d*.md")):
                if not re.fullmatch(re.escape(s) + r"-d[0-9]+\.md", os.path.basename(df)): continue
                for di in (tri_items(open(df, errors="ignore").read()) or []):
                    if not isinstance(di, dict): continue
                    bi = byid.get(str(di.get("id")))
                    if bi is not None and not str(di.get("id", "")).startswith(s + "-d"):
                        fb = list(bi.get("found_by") or []); fb += [x for x in (di.get("found_by") or []) if x not in fb]
                        bi["found_by"] = fb
                    else:
                        items.append(di); byid[str(di.get("id"))] = di
        sl.append({"slice": s, "state": st, "by": sorted(who.get(s, set())), "items": [
            {k: i.get(k) for k in ("id","title","severity","verdict","file","line","found_by","summary")} for i in (items or []) if isinstance(i, dict)]})
    judges = {}  # v2.5 panel: each judge writes out/<judge-lane>/<slice>.md, the merge writes out/triage/
    for d in sorted(glob.glob(f"{T}/out/*")):
        jl = os.path.basename(d)
        if jl == "triage" or not os.path.isdir(d): continue
        cl = glob.glob(f"{d}/*.claimed")
        judges[jl] = {"done": len(glob.glob(f"{d}/*.md")), "running": len(cl),
                      "active": [{"slice": os.path.basename(c)[:-8], "secs": int(time.time() - os.path.getmtime(c))} for c in cl]}
    TRI.append({"app": app, "slices": sl, "judges": judges,
                "lanes": {l: tok_summary([r for r in trows if r["lane"] == l]) for l in sorted(set(r["lane"] for r in trows))}})
out["triage"] = TRI
out["routes"] = {k: sorted(v) for k, v in ROUTES.items()}
out["lanes"] = dict(LANES, **{f: LANES[r] for f, r in CUR.items() if r in LANES and f != r})
print(json.dumps(out))
