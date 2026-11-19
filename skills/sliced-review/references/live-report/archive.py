#!/usr/bin/env python3
"""Save one finished review into the project, so it can be pointed at later (v2.7).

  archive.py --app <app> --mode <mode> [--kits ~/work/sr-kits] [--repo <project root>]
             [--live <dir holding status.json / providers.json>] [--date YYYY-MM-DD]

Runs on the kits host (where lane.sh ran). Writes <repo>/docs/reviews/<date>-<mode>/:
  REVIEW.md      the document: models, providers, time, tokens, cost, findings, triage, files
  report.html    the live-report page, frozen at the end of the run
  snapshot.json  the collector's numbers behind both
  inputs/        _context.md, _trustmap.md, ORDER.md, queue.txt, slices/, prepass.md, hashes/,
                 the lanes.tsv rows that ran, models.md as it was
  lanes/<lane>/  every slice report; ledgers (tokens, seconds, provider) beside them
  triage/        every judge's verdicts and the merged triage, with their ledgers
  guard/         slice-guard.py results per lane report (bad citations, STALE, out-of-slice)
and adds one line to <repo>/docs/reviews/INDEX.md. The session writes findings.json and the
scorecard (Steps 10 and 12) into the same docs/reviews/ folder. Never deletes anything.
Python 3 stdlib only.
"""
import argparse, csv, datetime as dt, glob, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, "..", "templates")
SEV = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def sh(cmd, env=None, t=300):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=t, env=env).stdout
    except Exception:
        return ""


def copy(src, dst):
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("*.raw", "*.err", "*.claimed", "*.tmp", "__pycache__"))
    elif os.path.isfile(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def secs(s):
    s = int(s or 0)
    return f"{s // 3600}h {s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m {s % 60:02d}s"


def tok(n):
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e3 else str(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True)
    ap.add_argument("--mode", required=True)
    ap.add_argument("--kits", default=os.path.expanduser(os.environ.get("SR_KITS", "~/work/sr-kits")))
    ap.add_argument("--repo")
    ap.add_argument("--live")
    ap.add_argument("--final", help="the final merge + severity pass report (default: sev-<app>/out/*/final.md)")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()
    K = os.path.expanduser(a.kits)
    A = os.path.join(K, a.app)
    T = os.path.join(K, f"tri-{a.app}")
    repo = os.path.expanduser(a.repo or open(os.path.join(A, "WORKDIR")).read().strip())
    mode = re.sub(r"[^a-z0-9-]+", "-", a.mode.lower()).strip("-")
    out = os.path.join(repo, "docs", "reviews", f"{a.date}-{mode}")
    os.makedirs(out, exist_ok=True)

    # inputs
    for f in ("_context.md", "_trustmap.md", "ORDER.md", "queue.txt", "prepass.md", "WORKDIR"):
        copy(os.path.join(A, f), os.path.join(out, "inputs", f))
    for d in ("slices", "hashes"):
        copy(os.path.join(A, d), os.path.join(out, "inputs", d))
    copy(os.path.join(HERE, "..", "models.md"), os.path.join(out, "inputs", "models.md"))
    lanes_used = sorted(d for d in os.listdir(os.path.join(A, "out")) if os.path.isdir(os.path.join(A, "out", d))) \
        if os.path.isdir(os.path.join(A, "out")) else []
    if os.path.exists(os.path.join(K, "lanes.tsv")):
        rows = [l for l in open(os.path.join(K, "lanes.tsv")) if l.split("\t")[0] in lanes_used]
        open(os.path.join(out, "inputs", "lanes.tsv"), "w").writelines(rows)

    # lane reports + ledgers
    for lane in lanes_used:
        copy(os.path.join(A, "out", lane), os.path.join(out, "lanes", lane))
    for f in glob.glob(os.path.join(A, "ledger*.tsv")) + glob.glob(os.path.join(A, "tokens-*.tsv")):
        copy(f, os.path.join(out, "lanes", os.path.basename(f)))
    # triage
    if os.path.isdir(T):
        copy(os.path.join(T, "out"), os.path.join(out, "triage"))
        for f in glob.glob(os.path.join(T, "ledger*.tsv")) + glob.glob(os.path.join(T, "tokens-*.tsv")):
            copy(f, os.path.join(out, "triage", os.path.basename(f)))

    # guard results
    guard = os.path.join(TPL, "slice-guard.py")
    gsum = {}
    if os.path.isdir(os.path.join(A, "hashes")):
        for lane in lanes_used:
            for rep in sorted(glob.glob(os.path.join(A, "out", lane, "*.md"))):
                sl = os.path.basename(rep)[:-3]
                if not os.path.exists(os.path.join(A, "slices", f"{sl}.md")):
                    continue
                res = sh([sys.executable, guard, "check", A, sl, rep])
                if res.strip():
                    os.makedirs(os.path.join(out, "guard", lane), exist_ok=True)
                    open(os.path.join(out, "guard", lane, f"{sl}.json"), "w").write(res)
                    try:
                        j = json.loads(res)
                        g = gsum.setdefault(lane, {"bad": 0, "oos": 0, "stale": 0})
                        g["bad"] += sum(1 for c in j["citations"] if c["status"] in ("missing-file", "bad-line"))
                        g["oos"] += sum(1 for c in j["citations"] if c["status"] == "out-of-slice")
                        g["stale"] += len(j["stale"])
                    except Exception:
                        pass

    # snapshot + frozen report
    env = dict(os.environ, SR_KITS=K, SR_APPS=a.app)
    snap = sh([sys.executable, os.path.join(HERE, "collect.py")], env=env)
    open(os.path.join(out, "snapshot.json"), "w").write(snap)
    live = os.path.expanduser(a.live) if a.live else ""
    st = os.path.join(live, "status.json") if live else ""
    pv = os.path.join(live, "providers.json") if live else ""
    sh([sys.executable, os.path.join(HERE, "render.py"), os.path.join(out, "snapshot.json"),
        st if st and os.path.exists(st) else os.path.join(out, "none.json"),
        pv if pv and os.path.exists(pv) else os.path.join(out, "none.json"),
        os.path.join(out, "report.html"), f"{a.app} — sliced review {a.date} ({a.mode})"])
    for f in (st, pv):
        if f and os.path.exists(f):
            copy(f, os.path.join(out, os.path.basename(f)))

    # REVIEW.md
    try:
        D = json.loads(snap)
    except Exception:
        D = {}
    app = next((x for x in D.get("apps", []) if x["app"] == a.app), {"lanes": {}, "slices": 0})
    meta = D.get("lanes", {})
    slow = {}
    alias = {}  # lane -> its out folder name (alias.tsv), so the slowest slice lands on the right row
    if os.path.exists(os.path.join(K, "alias.tsv")):
        for l in open(os.path.join(K, "alias.tsv")):
            p = l.split()
            if len(p) >= 2: alias[p[0]] = p[1]
    for f in glob.glob(os.path.join(A, "ledger*.tsv")):
        for r in csv.DictReader(open(f), delimiter="\t"):
            if r.get("status") == "OK" and r.get("secs", "").isdigit():
                ln = alias.get(r["lane"], r["lane"])
                cur = slow.get(ln)
                if not cur or int(r["secs"]) > cur[0]:
                    slow[ln] = (int(r["secs"]), r["slice"])
    commit = sh(["git", "-C", repo, "rev-parse", "--short", "HEAD"]).strip() or "n/a"
    L = [f"# Sliced review — {a.app} — {a.date} — mode `{a.mode}`", "",
         f"- Repo: `{repo}` at commit `{commit}` (when archived). Slices: {app.get('slices', 0)}.",
         f"- Models: {len(app['lanes'])} lanes. Exact model ids and providers below; versions in `inputs/models.md`.",
         "- Findings below are RAW lane counts; the verified list is the triage section, `findings.json`",
         "  and the scorecard in `docs/reviews/`.", "",
         "## Models", "",
         "| lane | model | provider | slices | total time | avg | slowest slice | tokens in / cached / out | API-equiv. | findings | C | H | M | L | failures | guard: bad cites / out-of-slice / stale |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    tot = {"secs": 0, "in": 0, "ca": 0, "out": 0, "usd": 0.0, "f": 0}
    for lane, v in sorted(app["lanes"].items()):
        m = meta.get(lane, {})
        t = v.get("tokens") or {}
        tin = (t.get("in", 0) + t.get("cache_write", 0)) if t else 0
        fl = ", ".join(f"{k} {n}" for k, n in v.get("fails", {}).items()) or "–"
        g = gsum.get(lane, {})
        sw = slow.get(lane)
        L.append(f"| {lane} | `{m.get('model', '?')}` | {m.get('provider', '?')} | {v['done']}/{app.get('slices', 0)} | "
                 f"{secs(v.get('ok_secs'))} | {secs(v.get('avg_secs'))} | {f'{secs(sw[0])} ({sw[1]})' if sw else '–'} | "
                 f"{(tok(tin) + ' / ' + tok(t.get('cached', 0)) + ' / ' + tok(t.get('out', 0))) if t else 'not logged'} | "
                 f"{'$%.2f' % v['api_usd'] if v.get('api_usd') is not None else '–'} | {v['findings']} | "
                 + " | ".join(str(v['sev'][k]) for k in SEV)
                 + f" | {fl} | {g.get('bad', '–')} / {g.get('oos', '–')} / {g.get('stale', '–')} |")
        tot["secs"] += v.get("ok_secs") or 0; tot["in"] += tin; tot["ca"] += t.get("cached", 0) if t else 0
        tot["out"] += t.get("out", 0) if t else 0; tot["usd"] += v.get("api_usd") or 0; tot["f"] += v["findings"]
    L += ["", f"**Totals:** model time {secs(tot['secs'])} · tokens {tok(tot['in'])} in / {tok(tot['ca'])} cached / "
          f"{tok(tot['out'])} out · API-equivalent ${tot['usd']:.2f} · {tot['f']} raw findings.", ""]
    # the final merge + severity pass (Step 10) wins over per-slice judge rows when it exists
    fin = None
    fpath = a.final or next(iter(sorted(glob.glob(os.path.join(K, f"sev-{a.app}", "out", "*", "final.md")))), "")
    if fpath and os.path.exists(fpath):
        copy(fpath, os.path.join(out, "triage", "final.md"))
        blocks = re.findall(r"```json\s*(.*?)```", open(fpath, errors="ignore").read(), re.S)
        try:
            fin = json.loads(blocks[-1]) if blocks else None
        except Exception:
            fin = None
    tri = next((x for x in D.get("triage") or [] if x["app"] == a.app), None)
    if fin:
        groups = [g for g in fin.get("confirmed_groups", []) if (g.get("severity") or "").upper() != "FALSE-POSITIVE"]
        leads = fin.get("leads", [])
        rank = {k: n for n, k in enumerate(SEV)}
        L += ["## Triage (final merge + severity pass)", "",
              f"- Judges per slice: {', '.join(sorted(tri.get('judges') or {})) if tri else 'n/a'}. Final pass: `triage/final.md`.",
              f"- Confirmed root causes {len(groups)} ("
              + ", ".join(f"{k.lower()} {sum(1 for g in groups if (g.get('severity') or '').upper() == k)}" for k in SEV)
              + f"); open leads {sum(1 for l in leads if not l.get('folds_into'))} (+{sum(1 for l in leads if l.get('folds_into'))} folded); "
              f"judge splits decided {len(fin.get('splits', []))}.", "",
              "| id | severity | finding | rows | found by |", "|---|---|---|---|---|"]
        for g in sorted(groups, key=lambda g: rank.get((g.get("severity") or "").upper(), 9)):
            L.append(f"| {g.get('gid')} | {(g.get('severity') or '').upper()} | {str(g.get('title') or '').replace('|', '/')} | "
                     f"{len(g.get('rows') or [])} | {', '.join(g.get('lanes') or [])} |")
        L += ["", "| lead | severity | open question | folds into |", "|---|---|---|---|"]
        for l in leads:
            L.append(f"| {l.get('lid')} | {l.get('severity') or 'NONE'} | {str(l.get('title') or '').replace('|', '/')} | {l.get('folds_into') or '–'} |")
        L.append("")
    elif tri:
        items = [i for x in tri["slices"] for i in x["items"]]
        V = lambda i: (i.get("verdict") or "").upper()
        conf = [i for i in items if V(i) == "CONFIRMED"]
        L += ["## Triage", "",
              f"- Judges: {', '.join(sorted(tri.get('judges') or {})) or ', '.join(sorted(tri.get('lanes') or {})) or 'n/a'}",
              f"- Confirmed {len(conf)} (" + ", ".join(f"{k.lower()} {sum(1 for i in conf if (i.get('severity') or '').upper() == k)}" for k in SEV)
              + f"); needs validation {sum(1 for i in items if V(i) in ('NEEDS-VALIDATION', 'PLAUSIBLE'))}; "
              f"false positive {sum(1 for i in items if V(i) == 'FALSE-POSITIVE')}.", "",
              "| severity | finding | where | found by |", "|---|---|---|---|"]
        rank = {k: n for n, k in enumerate(SEV)}
        for i in sorted(conf, key=lambda i: rank.get((i.get("severity") or "").upper(), 9)):
            fb = i.get("found_by") or []
            L.append(f"| {(i.get('severity') or '').upper()} | {str(i.get('title') or '').replace('|', '/')} | "
                     f"`{i.get('file')}:{i.get('line')}` | {', '.join(fb) if isinstance(fb, list) else fb} |")
        L.append("")
    L += ["## Files in this folder", "",
          "- `report.html` — the live-report page frozen at the end; `snapshot.json` — its numbers.",
          "- `inputs/` — the brief, trust map, slices, queue, tool pre-pass, hashes, lane commands, models.md.",
          "- `lanes/<lane>/<slice>.md` — every slice report; `lanes/ledger*.tsv` — time, tokens, provider per run.",
          "- `triage/` — every judge's verdicts and the merged triage; `guard/` — citation and STALE checks.", ""]
    open(os.path.join(out, "REVIEW.md"), "w").write("\n".join(L))
    for junk in glob.glob(os.path.join(out, "none.json")):
        os.remove(junk)

    idx = os.path.join(repo, "docs", "reviews", "INDEX.md")
    if not os.path.exists(idx):
        open(idx, "w").write("# Reviews\n\nOne line per archived review. Newest last.\n\n")
    line = (f"- {a.date} — `{a.mode}` — {len(app['lanes'])} lanes, {app.get('slices', 0)} slices, "
            f"{tot['f']} raw findings, ${tot['usd']:.2f} API-equiv. — [{a.date}-{mode}/REVIEW.md]({a.date}-{mode}/REVIEW.md)\n")
    if line not in open(idx).read():
        open(idx, "a").write(line)
    print(f"archived to {out}")


if __name__ == "__main__":
    main()
