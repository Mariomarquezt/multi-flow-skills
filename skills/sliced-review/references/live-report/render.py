#!/usr/bin/env python3
"""Render the live sliced-review report (one self-contained HTML page).

  render.py <snapshot.json> <status.json> <providers.json> <out.html> [project title]

snapshot.json  = collect.py output (lanes, slices, tokens, findings, triage)
status.json    = the Haiku monitor's check (summary, alerts, per-lane notes); may be missing
providers.json = pick-provider.py --providers (quota windows); may be missing
Model names come from models.md (model id -> short name). Python 3 stdlib only.
"""
import html, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS_MD = os.path.join(HERE, "..", "models.md")
e = lambda x: html.escape(str(x if x is not None else ""))
SEV = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
PROV = {"claude": "Claude", "codex": "Codex", "cursor": "Cursor", "xai": "xAI", "oc": "OpenCode Go",
        "opencodego": "OpenCode Go", "pi": "OpenCode Go (Pi)", "ocfree": "OpenCode free", "cmd": "Command Code",
        "cline": "Cline", "devin": "Devin", "spark": "Spark box"}


def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def short_names():
    """model id (and close variants) -> short name, from the models.md tables."""
    m = {}
    try:
        for line in open(MODELS_MD):
            r = re.match(r"\|\s*\*\*(.+?)\*\*\s*\|\s*([^|]+)\|\s*`([^`]+)`", line)
            if r:
                name, exact, mid = r.group(1), r.group(2).strip(), r.group(3)
                for k in (mid, mid.replace(".", "-"), re.sub(r"-(high|xhigh|max|medium)$", "", mid)):
                    m[k] = f"{name} ({exact})"
    except OSError:
        pass
    return m


def name_of(model, names):
    if not model:
        return "?"
    base = re.sub(r"-(high|xhigh|max|medium|low)$", "", model)
    return names.get(model) or names.get(base) or names.get(base.replace("-", ".")) or model


def secs(s):
    if not s:
        return "–"
    s = int(s)
    return f"{s // 3600}h {s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m {s % 60:02d}s"


def tok(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e3 else str(n)


def main():
    snap_p, stat_p, prov_p, out_p = sys.argv[1:5]
    title = sys.argv[5] if len(sys.argv) > 5 else ""
    D, S, P = load(snap_p, {}), load(stat_p, {}), load(prov_p, {})
    names = short_names()
    apps = D.get("apps", [])
    lanes_meta = D.get("lanes", {})
    project = title or ", ".join(a["app"] for a in apps) or "sliced review"
    lane_ids = sorted({l for a in apps for l in a["lanes"]})
    total_slices = sum(a["slices"] for a in apps if a.get("ready", True))

    # ---- per model rows ----
    rows, now_rows = [], []
    T = {"done": 0, "planned": 0, "run": 0, "find": 0, "sev": dict.fromkeys(SEV, 0), "secs": 0,
         "in": 0, "cached": 0, "out": 0, "usd": 0.0}
    for lane in lane_ids:
        vs = [(a, a["lanes"][lane]) for a in apps if lane in a["lanes"]]
        meta = lanes_meta.get(lane, {})
        mname = name_of(meta.get("model", lane), names)
        prov = PROV.get(meta.get("provider", ""), meta.get("provider", ""))
        done = sum(v["done"] for _, v in vs)
        planned = sum(a["slices"] for a, _ in vs)
        run = sum(v["running"] for _, v in vs)
        f = sum(v["findings"] for _, v in vs)
        sv = {k: sum(v["sev"][k] for _, v in vs) for k in SEV}
        okt = sum(v.get("ok_secs", 0) for _, v in vs)
        avg = [v["avg_secs"] for _, v in vs if v.get("avg_secs")]
        tk = [v["tokens"] for _, v in vs if v.get("tokens")]
        t_in = sum(t["in"] + t["cache_write"] for t in tk)
        t_ca = sum(t["cached"] for t in tk)
        t_out = sum(t["out"] for t in tk)
        usd = sum(v["api_usd"] for _, v in vs if v.get("api_usd") is not None)
        fails = {}
        for _, v in vs:
            for k, n in v.get("fails", {}).items():
                fails[k] = fails.get(k, 0) + n
        stopped = any(v.get("stopped") for _, v in vs)
        for a, v in vs:
            for act in v.get("active", []):
                now_rows.append((mname, prov, a["app"], act["slice"], act["secs"]))
        note = (S.get("lanes") or {}).get(lane, "")
        state = ("stop", "Stopped") if stopped else ("run", f"Active ×{run}") if run else \
                ("done", "Done") if planned and done >= planned else ("idle", "Waiting")
        T["done"] += done; T["planned"] += planned; T["run"] += run; T["find"] += f; T["secs"] += okt
        T["in"] += t_in; T["cached"] += t_ca; T["out"] += t_out; T["usd"] += usd
        for k in SEV:
            T["sev"][k] += sv[k]
        tok_cell = (f'{tok(t_in)} <small>in</small><br>{tok(t_ca)} <small>cached</small><br>{tok(t_out)} <small>out</small>'
                    if tk else '<small>not logged</small>')
        fl = ", ".join(f"{k.lower().replace('_', ' ')} {n}" for k, n in fails.items()) or "–"
        rows.append(
            f'<tr><th scope="row"><b>{e(mname)}</b><span class="sub">{e(prov)} · lane {e(lane)}</span></th>'
            f'<td><span class="pill p-{state[0]}">{state[1]}</span>{f"<span class=sub>{e(note)}</span>" if note else ""}</td>'
            f'<td class="n">{done}<small>/{planned}</small></td><td class="n">{secs(sum(avg) // len(avg) if avg else 0)}</td>'
            f'<td class="n">{secs(okt)}</td><td class="n">{tok_cell}</td><td class="n b">{f}</td>'
            + "".join(f'<td class="n s{k[0].lower()}">{sv[k] or "·"}</td>' for k in SEV)
            + f'<td class="n">{"$%.2f" % usd if usd else "<small>on plan</small>"}</td><td class="sub">{e(fl)}</td></tr>')

    # ---- app matrix (only when the run covers more than one app) ----
    matrix = ""
    if len(apps) > 1 and lane_ids:
        head = "".join(f'<th class="ah"><span>{e(a["app"])}</span><small>{a["slices"]} slices</small></th>' for a in apps)
        body = []
        for lane in lane_ids:
            cells = []
            for a in apps:
                v = a["lanes"].get(lane)
                if not v:
                    cells.append('<td class="c">–</td>'); continue
                pct = int(100 * v["done"] / a["slices"]) if a["slices"] else 0
                cls = "run" if v["running"] else "done" if v["done"] >= a["slices"] else "part" if v["done"] else "idle"
                cells.append(f'<td class="c c-{cls}"><span>{v["done"]}/{a["slices"]}</span><i style="width:{pct}%"></i></td>')
            body.append(f'<tr><th scope="row">{e(name_of(lanes_meta.get(lane, {}).get("model", lane), names))}</th>{"".join(cells)}</tr>')
        matrix = f'<section><h2>Progress per project</h2><div class="scroll"><table class="mx"><thead><tr><th>Model</th>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div></section>'

    # ---- now running ----
    now_rows.sort(key=lambda r: -r[4])
    now_html = "".join(f'<li><b>{e(m)}</b> <span class="sub">{e(p)}</span> → {e(app)} / <code>{e(sl)}</code> <span class="n">{secs(t)}</span></li>'
                       for m, p, app, sl, t in now_rows) or '<li class="sub">Nothing is running right now.</li>'

    # ---- triage ----
    TRI = D.get("triage") or []
    t_tot = sum(len(a["slices"]) for a in TRI)
    t_done = sum(1 for a in TRI for x in a["slices"] if x["state"] == "done")
    items = [(a["app"], x, i) for a in TRI for x in a["slices"] for i in x["items"]]
    V = lambda i: (i.get("verdict") or "").upper()
    conf = [t for t in items if V(t[2]) == "CONFIRMED"]
    nv = [t for t in items if V(t[2]) in ("NEEDS-VALIDATION", "PLAUSIBLE")]
    fp = [t for t in items if V(t[2]) == "FALSE-POSITIVE"]
    csev = {k: sum(1 for t in conf if (t[2].get("severity") or "").upper() == k) for k in SEV}
    judge_rows = []
    for a in TRI:
        for jl, j in (a.get("judges") or {}).items():
            act = ", ".join(f'{x["slice"]} ({secs(x["secs"])})' for x in j.get("active", []))
            jm = name_of(lanes_meta.get(jl, {}).get("model", jl), names)
            judge_rows.append(f'<tr><th scope="row">{e(jm)}<span class="sub">{e(a["app"])}</span></th><td class="n">{j["done"]}<small>/{len(a["slices"])}</small></td><td class="sub">{e(act) or "–"}</td></tr>')
    rank = {k: n for n, k in enumerate(SEV)}
    top = sorted([t for t in conf if (t[2].get("severity") or "").upper() in ("CRITICAL", "HIGH")],
                 key=lambda t: (rank.get((t[2].get("severity") or "").upper(), 9), -len(t[2].get("found_by") or [])))
    top_html = "".join(
        f'<tr><td><span class="pill s{(i.get("severity") or "x")[0].lower()}">{e((i.get("severity") or "").upper())}</span></td>'
        f'<td>{e(app)}</td><td><b>{e(i.get("title"))}</b><br><span class="sub">{e(str(i.get("summary") or "")[:240])}</span></td>'
        f'<td class="sub wrap">{e(i.get("file"))}:{e(i.get("line"))}</td><td class="n">{len(i.get("found_by") or [])}</td></tr>'
        for app, x, i in top[:40]) or '<tr><td colspan="5" class="sub">None yet.</td></tr>'
    tri_html = "" if not TRI else f"""<section><h2>Triage — three judges per slice</h2>
<div class="strip">
 <div class="stat"><span class="k">Slices triaged</span><span class="v">{t_done}<small>/{t_tot}</small></span></div>
 <div class="stat"><span class="k">Confirmed</span><span class="v">{len(conf)}</span><span class="sevline"><span class="sc">C {csev['CRITICAL']}</span><span class="sh">H {csev['HIGH']}</span><span class="sm">M {csev['MEDIUM']}</span><span class="sl">L {csev['LOW']}</span></span></div>
 <div class="stat"><span class="k">Needs validation</span><span class="v">{len(nv)}</span></div>
 <div class="stat"><span class="k">False positives</span><span class="v">{len(fp)}</span></div>
</div>
<div class="scroll"><table><thead><tr><th>Judge</th><th class="n">Slices</th><th>Working on</th></tr></thead><tbody>{"".join(judge_rows) or '<tr><td colspan="3" class="sub">No judge has started.</td></tr>'}</tbody></table></div>
<h3>Confirmed critical and high</h3>
<div class="scroll"><table><thead><tr><th>Sev</th><th>Project</th><th>Finding</th><th>Where</th><th class="n">Models</th></tr></thead><tbody>{top_html}</tbody></table></div></section>"""

    # ---- providers ----
    prov_html = ""
    if P:
        cards = []
        for k, v in P.items():
            ws = "".join(f'<p>{"monthly" if w["minutes"] >= 40000 else "weekly" if w["minutes"] >= 10080 else "daily" if w["minutes"] >= 1440 else "5-hour"}: '
                         f'<b>{100 - w["used"]:.0f}% left</b>, resets in {w["hours"]:.0f} h</p>' for w in v.get("windows", []))
            cards.append(f'<div class="q"><h3>{e(PROV.get(k, k))}</h3>{ws or "<p class=sub>no data</p>"}</div>')
        prov_html = f'<section><h2>Subscriptions</h2><p class="sub">From codexbar, Command Code and Cline. The picker spends the tokens that expire first.</p><div class="qs">{"".join(cards)}</div></section>'

    # ---- monitor ----
    alerts = "".join(f"<li>{e(a)}</li>" for a in (S.get("alerts") or []))
    mon = f"""<section class="mon"><h2>Monitor check <small>Haiku 5.5 · {e(S.get('checked', 'not run yet'))}</small></h2>
<p>{e(S.get('summary') or 'The monitor has not checked this run yet.')}</p>{f'<ul class="alerts">{alerts}</ul>' if alerts else ''}</section>"""

    page = f"""<title>Sliced Review Live</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
:root{{--bg:#f4f5f2;--panel:#fff;--ink:#1c2320;--mut:#5d6964;--line:#dadfd9;--acc:#0f6b5c;--run:#2c78cf;--done:#1f8a4c;--stop:#b24e2a;--part:#c4951a;--c:#a3122a;--h:#c2410c;--m:#a16207;--l:#47645a;--soft:#eef1ed}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#121614;--panel:#1a201d;--ink:#e3e8e5;--mut:#98a59f;--line:#2c3531;--acc:#4fc2a8;--run:#5aa2f0;--done:#4cc07a;--stop:#e07a52;--part:#e0b84a;--c:#f47185;--h:#fb923c;--m:#facc15;--l:#9fbfb2;--soft:#202824;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#121614;--panel:#1a201d;--ink:#e3e8e5;--mut:#98a59f;--line:#2c3531;--acc:#4fc2a8;--run:#5aa2f0;--done:#4cc07a;--stop:#e07a52;--part:#e0b84a;--c:#f47185;--h:#fb923c;--m:#facc15;--l:#9fbfb2;--soft:#202824;color-scheme:dark}}
body{{background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,"Segoe UI",Inter,sans-serif;padding-block:20px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}}
main{{max-width:1240px;margin:0 auto;display:grid;gap:16px}}
h1{{font-size:24px;margin:0;text-wrap:balance}} h2{{font-size:15px;margin:0 0 10px}} h3{{font-size:13px;margin:14px 0 8px}}
section{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;min-width:0}}
.sub{{color:var(--mut);font-size:12px;display:block}} small{{color:var(--mut);font-weight:400}}
.strip{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px}} .stat{{background:var(--soft);border-radius:8px;padding:8px 12px;min-width:120px;display:grid}}
.k{{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}} .v{{font-size:20px;font-weight:700;font-variant-numeric:tabular-nums}}
.sevline{{display:flex;gap:8px;font-weight:700;font-size:13px}} .sc{{color:var(--c)}} .sh{{color:var(--h)}} .sm{{color:var(--m)}} .sl{{color:var(--l)}}
.scroll{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}}
thead th{{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}} .n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}} .b{{font-weight:700}}
.pill{{display:inline-block;font-size:11px;font-weight:700;padding:1px 7px;border-radius:99px;border:1px solid currentColor}}
.p-run{{color:var(--run)}} .p-done{{color:var(--done)}} .p-stop{{color:var(--stop)}} .p-idle{{color:var(--mut)}}
.pill.sc,.pill.sh{{border-color:currentColor}}
.mx td.c{{min-width:70px;position:relative;font-size:12px}} .mx td.c i{{position:absolute;left:0;bottom:0;height:3px;background:var(--part)}}
.c-done i{{background:var(--done)!important}} .c-run i{{background:var(--run)!important}} .c-run span{{color:var(--run);font-weight:700}}
.ah span{{display:block}} .now{{margin:0;padding-left:18px;display:grid;gap:4px}} .wrap{{overflow-wrap:anywhere}}
.qs{{display:flex;flex-wrap:wrap;gap:10px}} .q{{background:var(--soft);border-radius:8px;padding:8px 12px;min-width:170px}} .q h3{{margin:0 0 4px}} .q p{{margin:2px 0;font-size:12px}}
.mon{{border-left:4px solid var(--acc)}} .alerts{{margin:6px 0 0;padding-left:18px;color:var(--stop)}}
</style>
<main>
<header><h1>{e(project)}</h1><span class="sub">Sliced review · updated {e(D.get('generated', time.strftime('%Y-%m-%d %H:%M')))} · refreshes every 4 minutes</span></header>
{mon}
<section><h2>Totals</h2><div class="strip">
 <div class="stat"><span class="k">Slices</span><span class="v">{total_slices}</span></div>
 <div class="stat"><span class="k">Slice reviews done</span><span class="v">{T['done']}<small>/{T['planned']}</small></span></div>
 <div class="stat"><span class="k">Active now</span><span class="v">{T['run']}</span></div>
 <div class="stat"><span class="k">Findings (raw)</span><span class="v">{T['find']}</span><span class="sevline"><span class="sc">C {T['sev']['CRITICAL']}</span><span class="sh">H {T['sev']['HIGH']}</span><span class="sm">M {T['sev']['MEDIUM']}</span><span class="sl">L {T['sev']['LOW']}</span></span></div>
 <div class="stat"><span class="k">Model time</span><span class="v">{secs(T['secs'])}</span></div>
 <div class="stat"><span class="k">Tokens</span><span class="v" style="font-size:15px">{tok(T['in'])} in · {tok(T['cached'])} cached · {tok(T['out'])} out</span></div>
 <div class="stat"><span class="k">API-equivalent</span><span class="v">${T['usd']:.2f}</span></div>
</div>
<h3>Active right now</h3><ul class="now">{now_html}</ul></section>
<section><h2>Models</h2><div class="scroll"><table><thead><tr><th>Model</th><th>State</th><th class="n">Slices</th><th class="n">Avg</th><th class="n">Total time</th><th class="n">Tokens</th><th class="n">Findings</th><th class="n sc">C</th><th class="n sh">H</th><th class="n sm">M</th><th class="n sl">L</th><th class="n">Cost</th><th>Failures</th></tr></thead><tbody>{"".join(rows) or '<tr><td colspan="13" class="sub">No lane has started.</td></tr>'}</tbody></table></div>
<p class="sub">Findings are what each model reported before triage; many are the same bug seen by several models. Model time adds up finished slices (lanes run in parallel). Tokens: in = new input incl. cache writes, cached = read from cache, out = written. Cost = API-equivalent; subscription runs are not billed per token.</p></section>
{matrix}
{tri_html}
{prov_html}
</main>"""
    tmp = out_p + ".tmp"
    open(tmp, "w").write(page)
    os.replace(tmp, out_p)


if __name__ == "__main__":
    main()
