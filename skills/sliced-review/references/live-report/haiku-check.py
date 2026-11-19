#!/usr/bin/env python3
"""The monitor check: Haiku 5.5 reads the run's facts and writes status.json for the report.

  haiku-check.py <snapshot.json> <providers.json> <status.json>

Builds a short fact sheet from the collector snapshot (no finding text, no code), asks Haiku 5.5
through `claude -p` for a plain-words summary, alerts and one note per lane, and writes status.json.
If Haiku fails, it keeps the last summary and adds an alert. Exit 0 = the run is finished
(every lane and judge done, nothing active); exit 1 = still running.
"""
import json, os, subprocess, sys, time

MODEL = "claude-haiku-5-5"   # the user's choice for the monitor (models.md -> Haiku)


def load(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def facts(D, P):
    lanes, finished = [], True
    for lane, meta in (D.get("lanes") or {}).items():
        vs = [(a, a["lanes"][lane]) for a in D.get("apps", []) if lane in a["lanes"]]
        if not vs:
            continue
        done = sum(v["done"] for _, v in vs)
        planned = sum(a["slices"] for a, _ in vs)
        active = [f'{a["app"]}/{x["slice"]} {x["secs"] // 60}m' for a, v in vs for x in v.get("active", [])]
        avg = [v["avg_secs"] for _, v in vs if v.get("avg_secs")]
        fails = {}
        for _, v in vs:
            for k, n in v.get("fails", {}).items():
                fails[k] = fails.get(k, 0) + n
        stopped = any(v.get("stopped") for _, v in vs)
        last = max((v.get("last_ok") or "" for _, v in vs), default="")
        if not stopped and (done < planned or active):
            finished = False
        lanes.append({"lane": lane, "model": meta.get("model"), "provider": meta.get("provider"),
                      "done": done, "planned": planned, "active": active,
                      "avg_min": round(sum(avg) / len(avg) / 60, 1) if avg else None,
                      "fails": fails, "stopped": stopped, "last_ok": last})
    judges = []
    for t in D.get("triage") or []:
        n = len(t["slices"])
        merged = sum(1 for x in t["slices"] if x["state"] == "done")
        if merged < n:
            finished = False
        for jl, j in (t.get("judges") or {}).items():
            judges.append({"app": t["app"], "judge": jl, "done": j["done"], "of": n,
                           "active": [f'{x["slice"]} {x["secs"] // 60}m' for x in j.get("active", [])]})
        judges.append({"app": t["app"], "merged_triage": merged, "of": n,
                       "bad_json": sum(1 for x in t["slices"] if x["state"] == "bad-json")})
    quota = {k: v.get("why") for k, v in (P or {}).items()}
    return {"time": time.strftime("%Y-%m-%d %H:%M %Z"), "lanes": lanes, "triage": judges,
            "subscriptions": quota, "host": D.get("host")}, finished


PROMPT = """You watch a multi-model code review while it runs. Below is a JSON fact sheet. Write ONLY a JSON
object, no prose around it, with these keys:
"summary": 2-3 short plain sentences: how far the run is, what is active, anything wrong.
"alerts": a list of short strings, one per real problem, [] if none. A problem is: a slice active
  longer than 3x that lane's avg_min (or longer than 45 min when avg is unknown); a lane with fails
  that keeps failing; a stopped lane that still has slices left; a subscription THAT A LANE IN
  "lanes" USES (its provider) with a window 90% or more used ("<provider>: a window is X% used");
  a full subscription no lane uses is not a problem; triage bad_json; the host low on memory.
"lanes": an object {lane id: one short note} for lanes that are active, stuck, failing or stopped.
Use plain words. Never invent numbers that are not in the facts.

FACTS:
"""


def main():
    snap, prov, out = sys.argv[1:4]
    D, P, old = load(snap, {}), load(prov, {}), load(out, {})
    F, finished = facts(D, P)
    status = dict(old)
    try:
        r = subprocess.run(["claude", "-p", "--model", MODEL, "--max-turns", "1"],
                           input=PROMPT + json.dumps(F), capture_output=True, text=True, timeout=180)
        txt = r.stdout.strip()
        j = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
        status = {"summary": j.get("summary", ""), "alerts": j.get("alerts") or [], "lanes": j.get("lanes") or {}}
    except Exception as ex:
        status.setdefault("alerts", [])
        status["alerts"] = [a for a in status["alerts"] if not a.startswith("Monitor check failed")] + \
                           [f"Monitor check failed at {F['time']} ({type(ex).__name__}); numbers below are still live."]
    status["checked"] = F["time"]
    status["finished"] = finished
    tmp = out + ".tmp"
    json.dump(status, open(tmp, "w"), indent=1)
    os.replace(tmp, out)
    sys.exit(0 if finished else 1)


if __name__ == "__main__":
    main()
