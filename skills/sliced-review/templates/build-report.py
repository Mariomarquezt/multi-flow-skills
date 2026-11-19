#!/usr/bin/env python3
"""Build the human-readable review report — Markdown AND a self-contained HTML page — from the
machine records a sliced review already writes:

  docs/reviews/findings.json          every distinct finding, status, severity, which review found it
  docs/reviews/scorecard-<date>.md    the per-model scorecard (Step 10)
  <review dir>/ledger.tsv             one line per slice run: time, status, cost (per model lane)

Usage:
  python3 build-report.py --project <repo root> [--date YYYY-MM-DD] [--out docs/reviews]

Writes  <out>/report-<date>.md  and  <out>/report-<date>.html . Standard library only.
Nothing here decides anything — it renders what triage already recorded. If the report looks wrong,
fix findings.json or the scorecard, then re-run.
"""
import argparse, datetime as dt, html, json, os, re, sys
from collections import Counter, defaultdict

SEV_ORDER = ["critical", "high", "medium", "low", "info"]
SEV_WEIGHT = {"critical": 8, "high": 4, "medium": 2, "low": 1, "info": 0}


# ---------- inputs ----------------------------------------------------------------------------

def load_findings(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def latest_scorecard(reviews_dir, date):
    if date:
        p = os.path.join(reviews_dir, f"scorecard-{date}.md")
        return p if os.path.exists(p) else None
    cands = sorted(f for f in os.listdir(reviews_dir) if re.fullmatch(r"scorecard-\d{4}-\d{2}-\d{2}\.md", f))
    return os.path.join(reviews_dir, cands[-1]) if cands else None


def parse_pipe_table(md):
    """First markdown pipe table in `md` -> (headers, rows). Rows are lists of cell strings."""
    lines = [l for l in md.splitlines()]
    i = 0
    while i < len(lines) and not (lines[i].startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1])):
        i += 1
    if i >= len(lines):
        return [], []
    split = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    headers = split(lines[i])
    rows = []
    for l in lines[i + 2:]:
        if not l.startswith("|"):
            break
        rows.append(split(l))
    return headers, rows


def parse_ledger(path):
    """ledger.tsv: date \t slice \t before->after \t N bytes \t MmSSs \t STATUS \t COST \t TOKENS \t API_USD
    (TOKENS = `in=.. cached=.. cache_write=.. out=..` and API_USD added 2026-10-15; older ledgers lack them)"""
    out = {"slices": 0, "seconds": 0, "slowest": (0, ""), "status": Counter(), "cost": [],
           "tokens": Counter(), "tok_runs": 0, "api_usd": 0.0, "api_runs": 0}
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            m = re.match(r"(\d+)m(\d+)s", parts[4])
            secs = int(m.group(1)) * 60 + int(m.group(2)) if m else 0
            out["slices"] += 1
            out["seconds"] += secs
            if secs > out["slowest"][0]:
                out["slowest"] = (secs, parts[1])
            out["status"][parts[5]] += 1
            if len(parts) > 6 and parts[6]:
                out["cost"].append(parts[6])
            if len(parts) > 7 and "out=" in parts[7]:
                out["tok_runs"] += 1
                for k, v in re.findall(r"(in|cached|cache_write|out)=(\d+)", parts[7]):
                    out["tokens"][k] += int(v)
            if len(parts) > 8:
                try:
                    out["api_usd"] += float(parts[8]); out["api_runs"] += 1
                except ValueError:
                    pass
    return out


def fmt_tokens(led):
    t = led["tokens"]
    if not led["tok_runs"]:
        return "not recorded"
    k = lambda n: f"{n/1e6:.1f}M" if n >= 1e6 else f"{n/1e3:.0f}k"
    return f"in {k(t['in'])} · cached {k(t['cached'])} · out {k(t['out'])} ({led['tok_runs']}/{led['slices']} runs)"


def fmt_usd(led):
    if not led["api_runs"]:
        return "unknown"
    return f"${led['api_usd']:.2f}" + ("" if led["api_runs"] == led["tok_runs"] else f" ({led['api_runs']} priced)")


def fmt_secs(s):
    h, r = divmod(int(s), 3600)
    m, s = divmod(r, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


# ---------- model ------------------------------------------------------------------------------

def build_model(data, scorecard_md, project_root):
    reviews = {r["id"]: r for r in data.get("reviews", [])}
    findings = data.get("findings", [])
    for f in findings:
        f.setdefault("severity", "info")
        f.setdefault("status", "open")
        f["model"] = reviews.get(f.get("review", ""), {}).get("model", f.get("review", "?"))

    by_sev = defaultdict(list)
    for f in findings:
        by_sev[f["severity"]].append(f)
    for sev in by_sev:
        by_sev[sev].sort(key=lambda f: (f["status"] != "open", not f.get("verified"), f.get("file") or ""))

    lanes = []
    for r in data.get("reviews", []):
        led = parse_ledger(os.path.join(project_root, r.get("dir", ""), "ledger.tsv")) if r.get("dir") else None
        mine = [f for f in findings if f.get("review") == r["id"]]
        lanes.append({
            "review": r,
            "ledger": led,
            "findings": mine,
            "verified": sum(1 for f in mine if f.get("verified")),
            "sev": Counter(f["severity"] for f in mine if f.get("verified")),
            "score": sum(SEV_WEIGHT.get(f["severity"], 0) for f in mine if f.get("verified")),
        })

    sc_headers, sc_rows = parse_pipe_table(scorecard_md) if scorecard_md else ([], [])
    sc_rest = ""
    if scorecard_md:
        idx = scorecard_md.find("\n## ")
        sc_rest = scorecard_md[idx:].strip() if idx >= 0 else ""

    return {
        "project": data.get("project", os.path.basename(os.path.abspath(project_root))),
        "updated_at": data.get("updated_at", ""),
        "findings": findings,
        "by_sev": by_sev,
        "status": Counter(f["status"] for f in findings),
        "verified_total": sum(1 for f in findings if f.get("verified")),
        "lanes": lanes,
        "scorecard": (sc_headers, sc_rows, sc_rest),
    }


# ---------- markdown ---------------------------------------------------------------------------

def md_table(headers, rows):
    if not headers:
        return "_no data_\n"
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def render_md(m, date):
    L = []
    L.append(f"# Review report — {m['project']} — {date}\n")
    total = len(m["findings"])
    L.append(f"**{total} distinct findings**, {m['verified_total']} verified. "
             + ", ".join(f"{m['status'][s]} {s}" for s in ("open", "fixed", "wontfix", "false-positive") if m["status"][s]) + ".\n")
    L.append("Severity counts below are verified findings only; unverified claims are listed but not counted.\n")

    L.append("## Findings by severity (verified / total)\n")
    L.append(md_table(["severity"] + SEV_ORDER,
                      [["verified"] + [sum(1 for f in m["by_sev"][s] if f.get("verified")) for s in SEV_ORDER],
                       ["total"] + [len(m["by_sev"][s]) for s in SEV_ORDER]]))

    L.append("\n## Model scorecard\n")
    h, rows, rest = m["scorecard"]
    if h:
        L.append(md_table(h, rows))
        if rest:
            L.append("\n" + rest + "\n")
    else:
        L.append("_No scorecard found — Step 10 did not write `scorecard-<date>.md`._\n")

    L.append("\n## Lanes — time and coverage per model\n")
    lrows = []
    for ln in m["lanes"]:
        r, led = ln["review"], ln["ledger"]
        if led:
            avg = led["seconds"] / led["slices"] if led["slices"] else 0
            st = ", ".join(f"{v} {k}" for k, v in led["status"].most_common())
            lrows.append([r.get("model", "?"), r.get("id", ""), led["slices"], fmt_secs(led["seconds"]), fmt_secs(avg),
                          f"{fmt_secs(led['slowest'][0])} ({led['slowest'][1]})", st, fmt_tokens(led), fmt_usd(led),
                          len(ln["findings"]), ln["verified"], ln["score"]])
        else:
            lrows.append([r.get("model", "?"), r.get("id", ""), r.get("slices", "?"), "no ledger", "", "", "", "", "", len(ln["findings"]), ln["verified"], ln["score"]])
    L.append(md_table(["model", "review id", "slices", "total time", "avg / slice", "slowest slice", "slice status", "tokens", "api_usd", "reported", "verified", "score"], lrows))

    for sev in SEV_ORDER:
        fs = m["by_sev"].get(sev, [])
        if not fs:
            continue
        L.append(f"\n## {sev.upper()} — {len(fs)}\n")
        for f in fs:
            mark = "✅" if f.get("verified") else "▫️"
            st = f["status"]
            fix = f" — fixed {f.get('fixed_at') or ''} `{f.get('fix_commit') or ''}`".rstrip(" `") if st == "fixed" else ""
            L.append(f"- {mark} **{f.get('title', '(untitled)')}** — `{f.get('file') or 'no file'}` — {st}{fix} — found by {f['model']}"
                     + (f"  \n  _{f['note']}_" if f.get("note") else ""))
    L.append("\n---\n_Generated by sliced-review `build-report.py` from `findings.json`, the scorecard and each lane's `ledger.tsv`. ✅ = verified by a person or a test; ▫️ = model claim, unverified._\n")
    return "\n".join(L)


# ---------- html -------------------------------------------------------------------------------

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#e3e3e3;--card:#f7f7f7;--crit:#b3261e;--high:#c7681c;--med:#8a6d00;--low:#2a6f97;--info:#6b6b6b;--ok:#2e7d32}
@media(prefers-color-scheme:dark){:root{--bg:#141414;--fg:#e8e8e8;--muted:#9a9a9a;--line:#2c2c2c;--card:#1d1d1d;--crit:#ff6b62;--high:#ffa25c;--med:#e0c04a;--low:#7db8dc;--info:#a0a0a0;--ok:#7bc47f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
main{max-width:1200px;margin:0 auto;padding:32px 24px}h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 12px;border-bottom:1px solid var(--line);padding-bottom:6px}
.sub{color:var(--muted);margin-bottom:24px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin:18px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px}.card b{display:block;font-size:24px}.card span{color:var(--muted);font-size:13px}
.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{border-bottom:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top;white-space:nowrap}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.03em}td.wrapcell{white-space:normal;min-width:260px}
.sev{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600;color:#fff}.sev.critical{background:var(--crit)}.sev.high{background:var(--high)}.sev.medium{background:var(--med)}.sev.low{background:var(--low)}.sev.info{background:var(--info)}
.st{font-size:12px;color:var(--muted)}.st.fixed{color:var(--ok)}.v{color:var(--ok);font-weight:600}.u{color:var(--muted)}code{background:var(--card);padding:1px 5px;border-radius:4px;font-size:12.5px}
.note{color:var(--muted);font-size:13px;white-space:normal}.rank1 td:first-child{font-weight:700}.prose{max-width:820px}.prose li{margin:4px 0}
footer{margin-top:40px;color:var(--muted);font-size:12.5px;border-top:1px solid var(--line);padding-top:12px}
@media print{main{padding:0}h2{break-after:avoid}tr{break-inside:avoid}}
"""


def esc(x):
    return html.escape(str(x if x is not None else ""))


def html_table(headers, rows, cls=None, wrap_cols=()):
    if not headers:
        return "<p class='u'>no data</p>"
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    trs = []
    for i, r in enumerate(rows):
        tds = "".join(f"<td class='{'wrapcell' if j in wrap_cols else ''}'>{c if isinstance(c, Raw) else esc(c)}</td>" for j, c in enumerate(r))
        trs.append(f"<tr class='{'rank1' if cls == 'score' and i == 0 else ''}'>{tds}</tr>")
    return f"<div class='wrap'><table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table></div>"


class Raw(str):
    """Already-escaped HTML fragment."""


def md_inline(s):
    """Tiny markdown → HTML for scorecard prose: bold, code, bullets, h2."""
    out = []
    for line in s.splitlines():
        t = esc(line)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
        if line.startswith("## "):
            out.append(f"<h3>{t[3:]}</h3>")
        elif line.startswith("- "):
            out.append(f"<li>{t[2:]}</li>")
        elif line.strip():
            out.append(f"<p>{t}</p>")
    s = "\n".join(out)
    return re.sub(r"((?:<li>.*?</li>\n?)+)", r"<ul>\1</ul>", s)


def render_html(m, date):
    total = len(m["findings"])
    cards = [(total, "distinct findings"), (m["verified_total"], "verified")] + \
            [(m["status"][s], s) for s in ("open", "fixed", "wontfix", "false-positive") if m["status"][s]] + \
            [(sum(1 for f in m["by_sev"][s] if f.get("verified")), f"verified {s}") for s in ("critical", "high") ]
    cards_html = "".join(f"<div class='card'><b>{esc(n)}</b><span>{esc(l)}</span></div>" for n, l in cards)

    h, rows, rest = m["scorecard"]
    sc = html_table(h, rows, cls="score") if h else "<p class='u'>No scorecard found — Step 10 did not write <code>scorecard-&lt;date&gt;.md</code>.</p>"
    sc_rest = f"<div class='prose'>{md_inline(rest)}</div>" if rest else ""

    lrows = []
    for ln in m["lanes"]:
        r, led = ln["review"], ln["ledger"]
        if led:
            avg = led["seconds"] / led["slices"] if led["slices"] else 0
            st = ", ".join(f"{v} {k}" for k, v in led["status"].most_common())
            lrows.append([r.get("model", "?"), r.get("id", ""), led["slices"], fmt_secs(led["seconds"]), fmt_secs(avg),
                          f"{fmt_secs(led['slowest'][0])} ({led['slowest'][1]})", st, fmt_tokens(led), fmt_usd(led),
                          len(ln["findings"]), ln["verified"], ln["score"]])
        else:
            lrows.append([r.get("model", "?"), r.get("id", ""), r.get("slices", "?"), "no ledger", "", "", "", "", "", len(ln["findings"]), ln["verified"], ln["score"]])
    lanes = html_table(["model", "review id", "slices", "total time", "avg / slice", "slowest slice", "slice status", "tokens", "api_usd", "reported", "verified", "score"], lrows)

    sections = []
    for sev in SEV_ORDER:
        fs = m["by_sev"].get(sev, [])
        if not fs:
            continue
        frows = []
        for f in fs:
            v = Raw("<span class='v'>verified</span>") if f.get("verified") else Raw("<span class='u'>unverified</span>")
            st = f["status"]
            stx = f"{st} · {f.get('fixed_at') or ''} {f.get('fix_commit') or ''}".strip(" ·") if st == "fixed" else st
            frows.append([Raw(f"<span class='sev {esc(sev)}'>{esc(sev)}</span>"), f.get("title", "(untitled)"),
                          Raw(f"<code>{esc(f.get('file') or 'no file')}</code>"), v, Raw(f"<span class='st {esc(st)}'>{esc(stx)}</span>"),
                          f["model"], Raw(f"<div class='note'>{esc(f.get('note') or '')}</div>")])
        sections.append(f"<h2>{esc(sev.upper())} <span class='u'>— {len(fs)}</span></h2>"
                        + html_table(["", "finding", "file", "", "status", "found by", "note"], frows, wrap_cols=(1, 6)))

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review report — {esc(m['project'])} — {esc(date)}</title><style>{CSS}</style></head><body><main>
<h1>Review report — {esc(m['project'])}</h1>
<div class="sub">{esc(date)} · findings.json updated {esc(m['updated_at'])} · severity counts are verified findings only</div>
<div class="cards">{cards_html}</div>
<h2>Model scorecard</h2>{sc}{sc_rest}
<h2>Lanes — time and coverage per model</h2>{lanes}
{''.join(sections)}
<footer>Generated by sliced-review <code>build-report.py</code> from <code>findings.json</code>, the scorecard and each lane's <code>ledger.tsv</code>.
Verified = a person or an executed test confirmed it. Unverified = a model's claim. Nothing in this page was decided by the generator.</footer>
</main></body></html>"""


# ---------- main -------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="project root (contains docs/reviews/findings.json)")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD; default = latest scorecard, else today")
    ap.add_argument("--out", default="docs/reviews", help="output dir, relative to --project")
    a = ap.parse_args()

    root = os.path.abspath(a.project)
    reviews_dir = os.path.join(root, "docs", "reviews")
    fpath = os.path.join(reviews_dir, "findings.json")
    if not os.path.exists(fpath):
        sys.exit(f"no findings.json at {fpath} — Step 12 has not run")

    sc_path = latest_scorecard(reviews_dir, a.date) if os.path.isdir(reviews_dir) else None
    date = a.date or (re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(sc_path)).group(1) if sc_path else dt.date.today().isoformat())
    scorecard_md = open(sc_path, encoding="utf-8").read() if sc_path else ""

    m = build_model(load_findings(fpath), scorecard_md, root)
    out_dir = os.path.join(root, a.out)
    os.makedirs(out_dir, exist_ok=True)
    md_out = os.path.join(out_dir, f"report-{date}.md")
    html_out = os.path.join(out_dir, f"report-{date}.html")
    with open(md_out, "w", encoding="utf-8") as f:
        f.write(render_md(m, date))
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(render_html(m, date))
    print(md_out)
    print(html_out)
    if not sc_path:
        print("warning: no scorecard found; report has no per-model ranking", file=sys.stderr)


if __name__ == "__main__":
    main()
