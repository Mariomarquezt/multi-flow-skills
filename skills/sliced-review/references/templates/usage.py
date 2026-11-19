#!/usr/bin/env python3
"""usage.py - token counts and API-equivalent cost for one model run (stdlib only).

  usage.py price <model-id> [--provider P] [--json]
      USD per 1M tokens (input, output, cache_read, cache_write) and where the price came from.
      Order: prices.json (skill) -> the runner's own table -> OpenRouter public list (cached 24h).
      A price found on OpenRouter is saved to prices.json with the date ("saved"), so it stays fixed.
      A free route (`-free`, a free plan) is priced as its paid twin. Prints `unknown` if nothing matches.

  usage.py capture --provider P --model M --cwd DIR --start ISO --end ISO [--raw F] [--err F] [--runner-model ID]
      One line: `tokens: in=.. cached=.. cache_write=.. out=.. source=.. api_usd=..`
      `in` is UNCACHED input everywhere; `out` includes reasoning tokens.

  usage.py backfill <ledger.tsv>...
      Writes tokens-<ledger name> next to each ledger (never touches the ledger itself; rows already
      filled there are kept, so Mac rows backfilled on the Mac and copied over survive a re-run).

  usage.py oc-log --runner NAME --cwd DIR --start EPOCH [--end EPOCH] [--model M] [--provider-id P]
      For OpenCode-driven runners: reads the run's session(s) from opencode.db, prints
      `<runner>: usage: in=.. cached=.. cache_write=.. out=.. model=.. session=.. api_usd=..` to stderr
      and appends one JSON line to $RUNNERS_DIR/opencode/usage.jsonl.

Token sources by provider: claude/cline/devin stderr lines, opencode.db (oc, ocfree, cesego, xai,
mimo, nexum), ~/.codex/sessions (codex), $RUNNERS_DIR/cursor/usage.jsonl (cursor),
~/.commandcode/projects (cmd), $RUNNERS_DIR/devin/usage.jsonl (devin, sums the --continue runs).
"""
import argparse, csv, datetime as dt, glob, json, os, re, sqlite3, sys, time, urllib.request

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.realpath(__file__))
OR_URL = "https://openrouter.ai/api/v1/models"          # public, no key, no billing
OR_CACHE = os.path.join(HOME, ".cache/sliced-review/openrouter-models.json")
OC_DB = os.path.join(HOME, ".local/share/opencode/opencode.db")
OC_PROVIDER = {"oc": "opencode-go", "ocfree": "opencode", "cesego": "cesego", "xai": "xai"}
EFFORT = re.compile(r"-(xhigh|high|medium|low|max|default|thinking)$")
SLACK_BEFORE, SLACK_AFTER = 20, 10          # seconds of clock slack around a run window

# ---------------------------------------------------------------- prices
def _load_json(p):
    try: return json.load(open(p))
    except Exception: return None

def _prices_file():
    for p in (os.environ.get("SR_PRICES", ""), os.path.join(HERE, "prices.json"),
              os.path.join(HERE, "..", "prices.json"),
              os.path.join(HOME, ".claude/skills/sliced-review/references/prices.json")):
        if p and os.path.exists(p): return p
    return None

def nk(s):  # comparison key: lower case, dots/underscores -> dashes
    return re.sub(r"[._]", "-", (s or "").lower().strip())

def forms(model):
    """Candidate names for one model id, most specific first."""
    m = (model or "").strip().split("/")[-1].split(":")[0].lower()
    out = [m]
    if m.startswith("cursor-"): m = m[7:]; out.append(m)   # Cursor's own ids: cursor-grok-4.6-high
    if m.endswith("-free"): m = m[:-5]; out.append(m)
    while EFFORT.search(m): m = EFFORT.sub("", m); out.append(m)
    seen, res = set(), []
    for f in out:
        if nk(f) not in seen: seen.add(nk(f)); res.append(f)
    return res

_OR = None
def openrouter_index():
    global _OR
    if _OR is not None: return _OR
    data = None
    fresh = os.path.exists(OR_CACHE) and time.time() - os.path.getmtime(OR_CACHE) < 86400
    if fresh: data = _load_json(OR_CACHE)
    if data is None:
        try:
            req = urllib.request.Request(OR_URL, headers={"User-Agent": "sliced-review-usage/1"})
            raw = urllib.request.urlopen(req, timeout=30).read()
            data = json.loads(raw)
            os.makedirs(os.path.dirname(OR_CACHE), exist_ok=True)
            open(OR_CACHE + ".tmp", "wb").write(raw); os.replace(OR_CACHE + ".tmp", OR_CACHE)
        except Exception:
            data = _load_json(OR_CACHE)          # stale is better than nothing
    idx = {}
    for m in (data or {}).get("data", []):
        i = m.get("id", "")
        if i.startswith("~") or ":" in i: continue
        p = m.get("pricing") or {}
        try: pi, po = float(p.get("prompt")), float(p.get("completion"))
        except (TypeError, ValueError): continue
        if pi < 0 or po < 0: continue
        e = {"in": pi * 1e6, "out": po * 1e6, "id": i}
        for k, src in (("cache_read", "input_cache_read"), ("cache_write", "input_cache_write")):
            try: e[k] = float(p[src]) * 1e6
            except (KeyError, TypeError, ValueError): pass
        idx.setdefault(nk(i.split("/")[-1]), e)
    _OR = idx
    return idx

def runner_tables(provider):
    """[(name, {key: entry})] — each runner's own price table, provider-specific first."""
    out = []
    d = _load_json(os.path.join(HOME, ".hermes/devin/prices.json"))
    if d:
        t = {}
        for k, v in d.get("models", {}).items():
            pr = v.get("price") or [0, 0, 0]
            if not any(pr) and v.get("price_after"): pr = v["price_after"]
            if any(pr): t[nk(k)] = {"in": pr[0], "cache_read": pr[1], "out": pr[2], "id": k}
        out.append(("devin", t))
    c = _load_json(os.path.join(HOME, ".hermes/scripts/claude-prices.json"))
    if c:
        t = {}
        for k, v in c.get("models", {}).items():
            pr = v.get("price") or []
            if len(pr) == 5 and any(pr):
                t[nk(k)] = {"in": pr[0], "cache_write": pr[1], "cache_read": pr[3], "out": pr[4], "id": k}
        out.append(("claude", t))
    if provider:
        out.sort(key=lambda x: x[0] != provider)
        out = [x for x in out if x[0] == provider]   # a runner's table prices only its own runs
    return out

_PCACHE = {}
def _save_price(name, o):
    """Save an OpenRouter price into prices.json with the date, so this model's price stays fixed
    for every later run (a price that moves would make old and new runs incomparable).
    Off with SR_PRICES_NOSAVE=1. Never raises: a read-only skill folder just skips the save."""
    if os.environ.get("SR_PRICES_NOSAVE") == "1": return
    pf = _prices_file() or os.path.join(HERE, "..", "prices.json")
    try:
        pj = _load_json(pf) or {}
        models = pj.setdefault("models", {})
        if any(nk(k) == nk(name) for k in models): return
        e = {k: round(o[k], 6) for k in ("in", "out", "cache_read", "cache_write") if k in o}
        e.update({"from": f"openrouter:{o['id']}", "saved": time.strftime("%Y-%m-%d")})
        models[name] = e
        tmp = pf + ".tmp"
        with open(tmp, "w") as f: json.dump(pj, f, indent=2); f.write("\n")
        os.replace(tmp, pf)
    except Exception:
        pass

def price(model, provider=""):
    key = (model, provider)
    if key in _PCACHE: return _PCACHE[key]
    pf = _prices_file(); pj = _load_json(pf) if pf else {}
    pj = pj or {}
    table = {nk(k): dict(v, id=k) for k, v in pj.get("models", {}).items()}
    aliases = {nk(k): v for k, v in pj.get("aliases", {}).items()}
    res = None
    for f in forms(model):
        names = []
        if provider and nk(f + "@" + provider) in aliases: names.append(aliases[nk(f + "@" + provider)])
        if nk(f) in aliases: names.append(aliases[nk(f)])
        names.append(f)
        for n in names:
            k = nk(n)
            if k in table: res = dict(table[k], source="prices.json"); break
            for tn, t in runner_tables(provider):
                if k in t: res = dict(t[k], source=f"runner:{tn}"); break
            if res: break
            o = openrouter_index().get(k)
            if o:
                res = dict(o, source=f"openrouter:{o['id']}")
                _save_price(n, o)
                break
        if res: break
    if res:
        res.setdefault("cache_read", res["in"] * 0.1)
        res.setdefault("cache_write", res["in"] * 1.25)
    _PCACHE[key] = res
    return res

def api_usd(tok, model, provider=""):
    p = price(model, provider)
    if not p or tok is None: return None
    return (tok["in"] * p["in"] + tok["cached"] * p["cache_read"] + tok["cache_write"] * p["cache_write"]
            + tok["out"] * p["out"]) / 1e6

# ---------------------------------------------------------------- helpers
def parse_ts(s):
    s = (s or "").strip()
    if not s: return None
    if re.match(r"^\d+(\.\d+)?$", s): return float(s)
    s = s.replace("Z", "+00:00")
    s = re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", s)
    try: return dt.datetime.fromisoformat(s).timestamp()
    except ValueError: return None

def T(i=0, c=0, w=0, o=0): return {"in": max(int(i), 0), "cached": int(c), "cache_write": int(w), "out": int(o)}
def add(a, b): return {k: a[k] + b[k] for k in a}
def g(text, k):
    m = re.search(rf"\b{k}=\$?(\d+)", text or "")
    return int(m.group(1)) if m else None

def same_model(a, b, provider=""):
    """True when two ids are the same model (after aliases)."""
    def canon(x):
        p = price(x, provider)
        return ("p", p["id"]) if p else ("n", nk(forms(x)[-1]))
    fa, fb = {nk(x) for x in forms(a)}, {nk(x) for x in forms(b)}
    return bool(fa & fb) or canon(a) == canon(b)

def pick(cands, start, end):
    """cands: [(t0, t1, tokens, label)]. Sequential runs inside the window are summed (retries);
    overlapping ones mean two concurrent runs -> take the one starting closest to start, mark ambiguous."""
    if not cands: return None, None
    cands = sorted(cands, key=lambda c: c[0])
    nz = [c for c in cands if any(c[2].values())]
    if not nz: return cands[0][2], "zero:" + ",".join(c[3] for c in cands)
    overlap = any(nz[i + 1][0] < nz[i][1] - 2 for i in range(len(nz) - 1))
    if overlap:
        # concurrent runs of the same model in the same folder: best start AND end fit wins;
        # only call it ambiguous when the runner-up fits almost as well (< 30 s apart)
        sc = sorted(nz, key=lambda c: abs(c[0] - start) + abs(c[1] - end))
        s0 = abs(sc[0][0] - start) + abs(sc[0][1] - end)
        s1 = abs(sc[1][0] - start) + abs(sc[1][1] - end)
        return sc[0][2], sc[0][3] + ("~ambiguous" if s1 - s0 < 30 else "~best-fit")
    tot = T()
    for c in nz: tot = add(tot, c[2])
    return tot, ",".join(c[3] for c in nz)

# ---------------------------------------------------------------- sources
def from_text(provider, text):
    """Parse a runner's own usage line. Returns normalized tokens or None."""
    t = text or ""
    if provider == "claude" or t.startswith("claude usage"):
        if g(t, "out") is None: return None
        return T(g(t, "in") or 0, g(t, "cache_read") or 0, g(t, "cache_write") or 0, g(t, "out"))
    if "cline-run:" in t or provider == "cline":
        m = re.search(r"in=(\d+) out=(\d+) cached=(\d+)", t)
        if not m: return None
        i, o, c = map(int, m.groups())
        return T(i - c, c, 0, o)                       # cline's in includes the cached part
    if "devin-run: usage" in t or provider == "devin":
        i, c, o = g(t, "in"), g(t, "cached"), g(t, "out")
        if o is None: return None
        return T((i or 0) - (c or 0), c or 0, 0, o)    # devin prompt_tokens include the cached part
    if t.startswith("tokens:") or ": usage: " in t:
        if g(t, "out") is None: return None
        return T(g(t, "in") or 0, g(t, "cached") or 0, g(t, "cache_write") or 0, g(t, "out"))
    return None

def _oc_db(db=OC_DB):
    if not os.path.exists(db): return None
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)

def oc_sessions(cwd, start, end, model="", provider_id="", db=OC_DB, provider=""):
    con = _oc_db(db)
    if not con: return []
    rows = con.execute(
        "select id, model, time_created, time_updated, tokens_input, tokens_output, tokens_reasoning,"
        " tokens_cache_read, tokens_cache_write, cost from session where parent_id is null and directory=?"
        " and time_created between ? and ?",
        (cwd, int((start - SLACK_BEFORE) * 1000), int((end + SLACK_AFTER) * 1000))).fetchall()
    out = []
    for sid, mj, t0, t1, ti, to, tr, cr, cw, cost in rows:
        try: m = json.loads(mj or "{}")
        except ValueError: m = {}
        if provider_id and m.get("providerID") and m.get("providerID") != provider_id: continue
        if model and m.get("id") and not same_model(m["id"], model, provider): continue
        tok = T(ti, cr, cw, (to or 0) + (tr or 0))
        for c in con.execute("with recursive k(id) as (select id from session where parent_id=? union all"
                             " select s.id from session s join k on s.parent_id=k.id)"
                             " select tokens_input,tokens_output,tokens_reasoning,tokens_cache_read,tokens_cache_write"
                             " from session where id in (select id from k)", (sid,)):
            tok = add(tok, T(c[0], c[3], c[4], (c[1] or 0) + (c[2] or 0)))
        out.append((t0 / 1000, t1 / 1000, tok, sid, m.get("id", ""), cost or 0))
    con.close()
    return out

_CODEX = None
def codex_index():
    global _CODEX
    if _CODEX is not None: return _CODEX
    _CODEX = []
    for f in glob.glob(os.path.join(HOME, ".codex/sessions/*/*/*/*.jsonl")):
        meta, model, last, t_end = None, "", None, None
        try:
            for line in open(f, errors="ignore"):
                if '"session_meta"' in line and meta is None:
                    try: meta = json.loads(line)["payload"]
                    except Exception: pass
                elif '"token_count"' in line:
                    last = line
                if not model and '"model":"' in line:
                    m = re.search(r'"model":"([^"]+)"', line)
                    if m and '"session_meta"' not in line: model = m.group(1)
            if last:
                j = json.loads(last); t_end = parse_ts(j.get("timestamp"))
        except Exception:
            continue
        if not meta: continue
        tok = None
        if last:
            u = (json.loads(last).get("payload", {}).get("info") or {}).get("total_token_usage") or {}
            c = u.get("cached_input_tokens", 0)
            tok = T(u.get("input_tokens", 0) - c, c, u.get("cache_write_input_tokens", 0), u.get("output_tokens", 0))
        _CODEX.append({"cwd": meta.get("cwd"), "t0": parse_ts(meta.get("timestamp")), "t1": t_end,
                       "model": model, "tok": tok, "id": meta.get("id", os.path.basename(f))})
    return _CODEX

def codex_runs(cwd, start, end, model):
    out = []
    for s in codex_index():
        if s["cwd"] != cwd or s["t0"] is None or not (start - SLACK_BEFORE <= s["t0"] <= end + SLACK_AFTER): continue
        if model and s["model"] and not same_model(s["model"], model, "codex"): continue
        out.append((s["t0"], s["t1"] or s["t0"], s["tok"] or T(), s["id"][:13]))
    return out

_CUR = None
def cursor_runs(cwd, start, end, model):
    global _CUR
    if _CUR is None:
        _CUR = []
        for line in open(os.path.join(HOME, ".hermes/cursor/usage.jsonl"), errors="ignore") if \
                os.path.exists(os.path.join(HOME, ".hermes/cursor/usage.jsonl")) else []:
            try: _CUR.append(json.loads(line))
            except ValueError: pass
    out = []
    for j in _CUR:
        t1 = parse_ts(j.get("ts")); dur = (j.get("duration_ms") or 0) / 1000
        if t1 is None or j.get("cwd") != cwd: continue
        t0 = t1 - dur
        if not (start - SLACK_BEFORE <= t0 and t1 <= end + SLACK_AFTER + 30): continue
        if model and not same_model(j.get("model", ""), model, "cursor"): continue
        out.append((t0, t1, T(j.get("input", 0), j.get("cache_read", 0), j.get("cache_write", 0), j.get("output", 0)),
                    (j.get("session_id") or "")[:8]))
    return out

def cmd_runs(cwd, start, end, model):
    d = os.path.join(HOME, ".commandcode/projects", cwd.replace("/", "-").lstrip("-"))
    out = []
    for f in glob.glob(os.path.join(d, "*.jsonl")):
        if f.endswith(".checkpoints.jsonl") or os.path.getmtime(f) < start - SLACK_BEFORE: continue
        t0 = t1 = None; tok = T(); models = set(); app_usd = 0.0
        for line in open(f, errors="ignore"):
            try: j = json.loads(line)
            except ValueError: continue
            ts = parse_ts(j.get("timestamp"))
            if ts: t0 = ts if t0 is None else t0; t1 = ts
            msg = j.get("message") or {}
            if isinstance(msg, dict):
                if msg.get("model"): models.add(msg["model"])
                u = msg.get("usage") or j.get("usage")
            else: u = j.get("usage")
            if isinstance(u, dict) and "outputTokens" in u:
                c = u.get("cacheReadTokens", 0) or 0
                tok = add(tok, T((u.get("inputTokens", 0) or 0) - c, c, u.get("cacheWriteTokens", 0) or 0, u.get("outputTokens", 0) or 0))
                app_usd += u.get("costUsd") or 0
        if t0 is None or not (start - SLACK_BEFORE <= t0 <= end + SLACK_AFTER): continue
        if model and models and not any(same_model(m, model, "cmd") for m in models): continue
        out.append((t0, t1 or t0, tok, os.path.basename(f)[:8]))
    return out

_DEV = None
def devin_runs(cwd, start, end, model):
    global _DEV
    if _DEV is None:
        p = os.path.join(HOME, ".hermes/devin/usage.jsonl"); _DEV = []
        for line in (open(p, errors="ignore") if os.path.exists(p) else []):
            try: _DEV.append(json.loads(line))
            except ValueError: pass
    out = []
    for j in _DEV:
        t1 = parse_ts(j.get("ts"))
        if t1 is None: continue
        t0 = t1 - (j.get("secs") or 0)
        c = j.get("cwd") or ""
        if not (c == cwd or c.startswith(cwd + ".dev")): continue
        if not (start - SLACK_BEFORE <= t0 and t1 <= end + SLACK_AFTER + 30): continue
        if model and j.get("model") and not same_model(j["model"], model, "devin"): continue
        out.append((t0, t1, T((j.get("in") or 0) - (j.get("cached") or 0), j.get("cached") or 0, 0, j.get("out") or 0),
                    c.rsplit(".", 1)[-1] if ".dev" in c else "main"))
    return out

def devin_pick(cands, start, end):
    """Each Devin slot has its own checkout (<workdir>.devN); one slice = the first run plus its --continue runs,
    all in ONE slot folder. Pick the folder whose runs fit the window best and sum them."""
    groups = {}
    for c in cands: groups.setdefault(c[3], []).append(c)
    if not groups: return None, None
    fit = lambda g: abs(min(x[0] for x in g) - start) + abs(max(x[1] for x in g) - end)
    best = sorted(groups.values(), key=fit)
    tok = T()
    for c in best[0]: tok = add(tok, c[2])
    amb = len(best) > 1 and fit(best[1]) - fit(best[0]) < 30
    return tok, f"{best[0][0][3]}x{len(best[0])}" + ("~ambiguous" if amb else "")

def capture(provider, model, cwd, start, end, raw="", err="", runner_model="", usage_text=""):
    """-> (tokens|None, source)"""
    cwd = os.path.realpath(os.path.expanduser(cwd)) if cwd else cwd
    text = usage_text
    if not text and err and os.path.exists(err):
        lines = [l for l in open(err, errors="ignore") if re.search(r"usage|in=\d", l)]
        text = lines[-1] if lines else ""
    m = runner_model or model
    if provider == "devin":
        tok, src = devin_pick(devin_runs(cwd, start, end, m), start, end)
        if tok is not None and any(tok.values()): return tok, "devin-usage.jsonl:" + src
    if provider in ("claude", "cline", "devin"):
        tok = from_text(provider, text)
        return (tok, f"{provider}-stderr") if tok else (None, f"no {provider} usage line")
    if provider in ("oc", "ocfree", "cesego", "xai", "mimo", "nexum", "opencode"):
        c = [(a, b, t, s) for a, b, t, s, _, _ in oc_sessions(cwd, start, end, m, OC_PROVIDER.get(provider, ""), provider=provider)]
        tok, src = pick(c, start, end)
        return (tok, "opencode.db:" + src) if tok is not None else (None, "no opencode session in window")
    if provider == "codex":
        tok, src = pick(codex_runs(cwd, start, end, m), start, end)
        return (tok, "codex-session:" + src) if tok is not None else (None, "no codex session in window")
    if provider == "cursor":
        tok, src = pick(cursor_runs(cwd, start, end, m), start, end)
        return (tok, "cursor-usage.jsonl:" + src) if tok is not None else (None, "no cursor usage line in window")
    if provider == "cmd":
        tok, src = pick(cmd_runs(cwd, start, end, m), start, end)
        return (tok, "commandcode:" + src) if tok is not None else (None, "no commandcode session in window")
    tok = from_text(provider, text)
    return (tok, "stderr") if tok else (None, f"no source for provider {provider}")

def fmt(tok, src, model, provider):
    if tok is None: return f"tokens: none source={src} api_usd=unknown"
    u = api_usd(tok, model, provider)
    p = price(model, provider)
    return (f"tokens: in={tok['in']} cached={tok['cached']} cache_write={tok['cache_write']} out={tok['out']}"
            f" source={src} api_usd={'unknown' if u is None else f'{u:.6f}'}"
            f" price={p['source'] if p else 'unknown'}")

# ---------------------------------------------------------------- commands
def cmd_price(a):
    p = price(a.model, a.provider)
    if a.json: print(json.dumps(p)); return 0
    if not p: print(f"{a.model}: unknown"); return 1
    print(f"{a.model}: in={p['in']:g} out={p['out']:g} cache_read={p['cache_read']:g} cache_write={p['cache_write']:g}"
          f" USD/1M source={p['source']}")
    return 0

def cmd_capture(a):
    s, e = parse_ts(a.start), parse_ts(a.end)
    tok, src = capture(a.provider, a.model, a.cwd, s, e, a.raw, a.err, a.runner_model)
    print(fmt(tok, src, a.model, a.provider))
    return 0

def _workdir(ledger, app):
    for d in (os.path.dirname(os.path.abspath(ledger)),):
        w = os.path.join(d, "WORKDIR")
        if os.path.exists(w): return open(w).read().strip()
        base = os.path.basename(d)
        if base.startswith("tri-"):   # triage kits read the app's tree
            w2 = os.path.join(os.path.dirname(d), base[4:], "WORKDIR")
            if os.path.exists(w2): return open(w2).read().strip()
    return ""

def _runner_models():
    """lane -> model id the runner passes (e.g. cesego/deepseek-v4-flash-max), from lanes.tsv next to the kits."""
    out = {}
    for p in (os.environ.get("SR_LANES", ""), os.path.join(HERE, "..", "lanes.tsv"), os.path.join(HERE, "lanes.tsv")):
        if p and os.path.exists(p):
            for l in open(p):
                f = l.rstrip("\n").split("\t")
                if len(f) >= 4:
                    m = re.search(r"--model[ =](\S+)", f[3])
                    if m: out[f[0]] = m.group(1).strip("'\"")
            break
    return out

def side_path(led):
    """tokens-<ledger name> next to the ledger. Deliberately NOT <ledger>.tokens.tsv: tools glob `ledger*.tsv`
    and would read the side file as a ledger."""
    return os.path.join(os.path.dirname(os.path.abspath(led)), "tokens-" + os.path.basename(led))

def cmd_backfill(a):
    rm = _runner_models()
    for led in a.ledgers:
        rows = list(csv.DictReader(open(led), delimiter="\t"))
        wd = a.cwd or _workdir(led, "")
        side = side_path(led)
        stats = {}
        # never lose a row an earlier backfill filled (e.g. Mac rows backfilled on the Mac, copied here)
        prev = {}
        if os.path.exists(side):
            for r in csv.DictReader(open(side), delimiter="\t"):
                if any((r.get(k) or "0") != "0" for k in ("in", "cached", "cache_write", "out")):
                    prev[(r["slice"], r["lane"], r["ts"])] = r
        with open(side + ".new", "w") as fh:
            fh.write("slice\tlane\tts\tin\tcached\tcache_write\tout\tapi_usd\tsource\n")
            for r in rows:
                end = parse_ts(r.get("ts")); secs = int(r.get("secs") or 0)
                prov, model, lane = r.get("provider", ""), r.get("model", ""), r.get("lane", "")
                tok, src = None, "bad row"
                pr = prev.get((r.get("slice", ""), lane, r.get("ts", "")))
                if pr:   # already filled: keep it (only the price is recomputed)
                    tok = T(pr["in"], pr["cached"], pr["cache_write"], pr["out"]); src = pr["source"]
                elif end:
                    tok, src = capture(prov, model, wd, end - secs, end, runner_model=rm.get(lane, ""),
                                       usage_text=r.get("usage", ""))
                u = api_usd(tok, model, prov) if tok else None
                st = stats.setdefault(lane, {"rows": 0, "filled": 0, "why": {}})
                st["rows"] += 1
                if tok is not None and any(tok.values()): st["filled"] += 1
                else:
                    why = src.split(":")[0] if tok is None else "zero tokens (run died before a request)"
                    st["why"][why] = st["why"].get(why, 0) + 1
                fh.write("\t".join([r.get("slice", ""), lane, r.get("ts", "")] +
                         ([str(tok[k]) for k in ("in", "cached", "cache_write", "out")] if tok else ["", "", "", ""]) +
                         ["" if u is None else f"{u:.6f}", src]) + "\n")
        os.replace(side + ".new", side)
        print(f"# {led} -> {side}")
        for lane, st in sorted(stats.items()):
            print(f"  {lane:16} rows={st['rows']:4} filled={st['filled']:4} missing={st['rows']-st['filled']:4} "
                  + "; ".join(f"{k}={v}" for k, v in st["why"].items()))
    return 0

def cmd_oc_log(a):
    start = float(a.start); end = float(a.end) if a.end else time.time()
    cwd = os.path.realpath(a.cwd)
    ss = oc_sessions(cwd, start, end, a.model or "", a.provider_id or "")
    if not ss and os.path.abspath(a.cwd) != cwd:     # opencode may store the un-resolved path
        cwd = os.path.abspath(a.cwd); ss = oc_sessions(cwd, start, end, a.model or "", a.provider_id or "")
    # this run's sessions: started inside the window; concurrent runs of the same model are told apart by start time
    cands = [(t0, t1, tok, sid) for t0, t1, tok, sid, _, _ in ss]
    tok, src = pick(cands, start, end)
    mid = next((mm for *_, mm, _ in ss if mm), a.model or "")
    if tok is None:
        sys.stderr.write(f"{a.runner}: usage: none (no opencode session found in {cwd} since run start)\n"); return 0
    usd = api_usd(tok, a.model or mid, a.provider or "")
    p = price(a.model or mid, a.provider or "")
    sys.stderr.write(f"{a.runner}: usage: in={tok['in']} cached={tok['cached']} cache_write={tok['cache_write']} "
                     f"out={tok['out']} model={a.model or mid} session={src} "
                     f"api_usd={'unknown' if usd is None else f'{usd:.6f}'} price={p['source'] if p else 'unknown'}\n")
    rec = {"ts": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "runner": a.runner,
           "model": a.model or mid, "cwd": cwd, "session": src, "secs": round(end - start),
           "tokens": tok, "api_usd": None if usd is None else round(usd, 6),
           "price_source": p["source"] if p else None}
    log = os.path.expanduser(a.log)
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "a") as fh: fh.write(json.dumps(rec) + "\n")
    return 0

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("price"); p.add_argument("model"); p.add_argument("--provider", default=""); p.add_argument("--json", action="store_true")
    p = sp.add_parser("capture")
    for k in ("provider", "model", "cwd", "start", "end"): p.add_argument("--" + k, required=True)
    p.add_argument("--raw", default=""); p.add_argument("--err", default=""); p.add_argument("--runner-model", default="")
    p = sp.add_parser("backfill"); p.add_argument("ledgers", nargs="+"); p.add_argument("--cwd", default="")
    p = sp.add_parser("oc-log")
    p.add_argument("--runner", required=True); p.add_argument("--cwd", default=os.getcwd()); p.add_argument("--start", required=True)
    p.add_argument("--end", default=""); p.add_argument("--model", default=""); p.add_argument("--provider-id", default="")
    p.add_argument("--provider", default=""); p.add_argument("--log", default="$RUNNERS_DIR/opencode/usage.jsonl")
    a = ap.parse_args()
    return {"price": cmd_price, "capture": cmd_capture, "backfill": cmd_backfill, "oc-log": cmd_oc_log}[a.cmd](a)

if __name__ == "__main__":
    try: sys.exit(main())
    except BrokenPipeError: pass
