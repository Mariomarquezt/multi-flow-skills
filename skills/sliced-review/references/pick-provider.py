#!/usr/bin/env python3
"""Pick the subscription that runs a model: the one whose tokens expire first.

  pick-provider.py                 table: every model in models.md with its providers ranked
  pick-provider.py --model Grok    one line: the provider key to use (exit 1 if none is usable)
  pick-provider.py --json          the same data as JSON
  pick-provider.py --providers     JSON: every provider's windows (% used, length, hours to reset)

Providers come from the "providers (codexbar key)" column of models.md (the one source of truth).
For each provider it reads the weekly and monthly windows (codexbar, cmd-pool.py, cline-quota.py).
Score = % left / hours until that window resets, best long window wins: tokens that renew soonest
and are still unused go first. A provider with any window at 95% used or more is skipped.
Run on the Mac (codexbar lives there). Python 3 stdlib only. Never prints account names or keys.
"""
import datetime as dt, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "models.md")
BLOCK_AT = 95          # any window this full -> skip the provider
LONG_MIN = 7 * 24 * 60  # weekly or longer counts as a "renewal" window
NO_RESET_HOURS = 24 * 7 # rolling windows with no reset time are scored as if they reset in a week
KNOWN = {"claude", "codex", "cursor", "xai", "opencodego", "devin", "cmd", "cline", "ocfree", "antigravity"}
FREE = {"ocfree"}  # $0 tiers with no quota window: always usable, ranked after any paid window
CODEXBAR = {"claude": "claude", "codex": "codex", "cursor": "cursor", "xai": "grok",
            "opencodego": "opencodego", "devin": "devin", "antigravity": "antigravity"}


def sh(cmd, t=60):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t).stdout
    except Exception:
        return ""


def now():
    return dt.datetime.now(dt.timezone.utc)


def hours_to(iso):
    try:
        t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return max((t - now()).total_seconds() / 3600, 0.1)
    except Exception:
        return None


def roster():
    """{short name: [provider keys]} from the markdown tables in models.md."""
    out = {}
    for line in open(MODELS):
        m = re.match(r"\|\s*\*\*(.+?)\*\*\s*\|(.*)", line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) >= 3:
            keys = [k for k in re.findall(r"`([a-z]+)`", cells[2]) if k in KNOWN]
            if keys:
                out[m.group(1)] = keys
    return out


def windows_codexbar(key):
    raw = sh(f"codexbar usage --provider {CODEXBAR[key]} --format json 2>/dev/null")
    try:
        u = json.loads(raw)[0]["usage"]
    except Exception:
        return None
    ws = []
    for k in ("primary", "secondary", "tertiary"):
        w = u.get(k)
        if w and w.get("usedPercent") is not None:
            ws.append({"used": float(w["usedPercent"]), "minutes": w.get("windowMinutes") or 0,
                       "hours": hours_to(w.get("resetsAt", "")) or NO_RESET_HOURS})
    return ws or None


def windows_cline():
    txt = sh(os.path.expanduser("$RUNNERS_DIR/cline/cline-quota.py") + " 2>/dev/null")
    end = re.search(r"period ends (\S+)", txt)
    ws = []
    for name, mins in (("5h", 300), ("7d", 10080), ("30d", 43200)):
        m = re.search(rf"^\s*{name}\s.*?([\d.]+)%\s*$", txt, re.M)
        if m:
            hrs = hours_to(end.group(1)) if (end and name == "30d") else NO_RESET_HOURS
            ws.append({"used": float(m.group(1)), "minutes": mins, "hours": hrs or NO_RESET_HOURS})
    return ws or None


def windows_cmd():
    txt = sh("python3 " + os.path.expanduser("$RUNNERS_DIR/cmd/cmd-pool.py") + " status 2>/dev/null")
    best = None
    for line in txt.splitlines()[1:]:
        p = line.split()
        if len(p) < 7 or p[1] != "yes" or p[2] not in ("-", ""):
            continue
        try:
            h_used, h_cap = map(float, p[4].split("/"))
            w_used, w_cap = map(float, p[5].split("/"))
        except ValueError:
            continue
        ws = [{"used": 100 * h_used / h_cap if h_cap else 100, "minutes": 300, "hours": 5},
              {"used": 100 * w_used / w_cap if w_cap else 100, "minutes": 10080, "hours": NO_RESET_HOURS}]
        if best is None or ws[1]["used"] < best[1]["used"]:
            best = ws  # cmd-run.sh itself picks the account with the most left
    return best


def score(ws):
    """(score, reason) or (None, reason) when the provider is not usable."""
    if not ws:
        return None, "no quota data"
    full = [w for w in ws if w["used"] >= BLOCK_AT]
    if full:
        return None, f"a window is {full[0]['used']:.0f}% used"
    long = [w for w in ws if w["minutes"] >= LONG_MIN] or ws
    # windows that reset together are one budget: the tightest of them is what is really left
    tight = {}
    for w in long:
        k = round(w["hours"])
        if k not in tight or w["used"] > tight[k]["used"]:
            tight[k] = w
    best = max(tight.values(), key=lambda w: (100 - w["used"]) / w["hours"])
    s = (100 - best["used"]) / best["hours"]
    kind = "monthly" if best["minutes"] >= 40000 else ("weekly" if best["minutes"] >= LONG_MIN else "short")
    return s, f"{kind} {100 - best['used']:.0f}% left, resets in {best['hours']:.0f} h"


def windows(k):
    return windows_cline() if k == "cline" else windows_cmd() if k == "cmd" else \
           windows_codexbar(k) if k in CODEXBAR else None


def main():
    args = sys.argv[1:]
    if "--providers" in args:
        out = {}
        for k in sorted(KNOWN):
            ws = None if k in FREE else windows(k)
            sc, why = (0.0, "free tier: no quota window, $0") if k in FREE else score(ws)
            out[k] = {"windows": ws or [], "score": sc, "why": why}
        print(json.dumps(out, indent=1))
        return
    want = args[args.index("--model") + 1] if "--model" in args else None
    R = roster()
    if want and want not in R:
        sys.exit(f"unknown model {want!r}; models.md has: {', '.join(R)}")
    cache, result = {}, {}
    for model, keys in R.items():
        if want and model != want:
            continue
        ranked = []
        for k in keys:
            if k not in cache:
                cache[k] = (0.0, "free tier: no quota window, $0") if k in FREE else score(windows(k))
            s, why = cache[k]
            ranked.append({"provider": k, "score": round(s, 3) if s is not None else None, "why": why})
        ranked.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0)))
        result[model] = ranked
    if "--json" in args:
        print(json.dumps(result, indent=1))
        return
    if want:
        top = result[want][0]
        if top["score"] is None:
            sys.exit(f"{want}: no usable provider ({'; '.join(r['provider'] + ': ' + r['why'] for r in result[want])})")
        print(top["provider"])
        return
    for model, ranked in result.items():
        print(f"{model}:")
        for i, r in enumerate(ranked):
            mark = "→" if i == 0 and r["score"] is not None else " "
            print(f"  {mark} {r['provider']:<11} {r['why']}")


if __name__ == "__main__":
    main()
