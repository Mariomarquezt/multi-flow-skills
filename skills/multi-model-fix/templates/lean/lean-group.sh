#!/bin/bash
# Run ONE group of sub-tasks on autopilot: helper run, gate, next sub-task. Returns at once.
# Groups that edit no file in common run at the same time, each in its own worktree.
# usage: lean-group.sh <group> <worktree> <briefs dir> <logs dir> <step> [<step>...]
#   per step the lead wrote:  <briefs dir>/<step>.md        the sub-task brief
#                             <briefs dir>/gate-<step>.sh   the sub-task gate (runs in the worktree; exit 0 = green)
#   env: LEAN_TAG (required), LEAN_MAX_REQ (default 80000: a helper conversation whose last run had a
#        request above this starts fresh for the next step), LEAN_HELPER, LEAN_TIMEOUT, DEVIN_RUNNER
# It stops at the first step that is still red after ONE automatic return, or that ends with
# STOPPED / NOT REPRODUCED. Result: <logs dir>/<group>.done = "GREEN" or "RED <step> <why>",
# <logs dir>/<group>.summary = end of each helper log + the gate lines. Wait with lean-wait.sh.
set -u
[ $# -ge 5 ] || { sed -n '2,12p' "$0"; exit 2; }
group=$1; wt=$2; briefs=$3; logs=$4; shift 4
: "${LEAN_TAG:?set LEAN_TAG}"
here=$(cd "$(dirname "$0")" && pwd)
[ -d "$wt" ] || { echo "lean-group: no worktree $wt"; exit 2; }
mkdir -p "$logs"; logs=$(cd "$logs" && pwd); briefs=$(cd "$briefs" && pwd); wt=$(cd "$wt" && pwd)
for s in "$@"; do for f in "$briefs/$s.md" "$briefs/gate-$s.sh"; do [ -s "$f" ] || { echo "lean-group: missing $f"; exit 2; }; done; done
rm -f "$logs/$group.done" "$logs/$group.summary"
usage=${LEAN_USAGE_FILE:-$HOME/.hermes/devin/usage.jsonl}
tl() { echo "$(date -u +%FT%TZ) $*" >> "$logs/timeline.txt"; }
maxreq() { python3 - "$usage" "$LEAN_TAG-$1" <<'PY' 2>/dev/null || echo 0
import json,sys
m=0
try:
    for l in open(sys.argv[1]):
        try: d=json.loads(l)
        except Exception: continue
        if d.get("tag")==sys.argv[2]: m=d.get("max_req") or 0
except Exception: pass
print(m)
PY
}
run_one() {   # <mode> <step> <brief file>   foreground; waits out a rate limit up to 3 times
  local mode=$1 step=$2 brief=$3 try=0 mins
  while :; do
    "$here/lean-run.sh" "$mode" "$wt" "$brief" "$logs" "$step" > /dev/null || return 9
    while [ ! -f "$logs/$step.done" ]; do sleep 3; done
    mins=$(grep -o 'limit will reset in [0-9]* minute' "$logs/$step.log" | tail -1 | grep -o '[0-9]*')
    if [ -n "$mins" ] && ! grep -q "^DONE\|^STOPPED\|^NOT REPRODUCED\|^REPRODUCED" "$logs/$step.log" && [ $try -lt 3 ]; then
      try=$((try + 1)); tl "$step rate limit: wait $((mins + 1)) min (try $try)"; sleep $(((mins + 1) * 60)); continue
    fi
    return 0
  done
}
gate() {      # <step>  -> 0 green
  ( cd "$wt" && bash "$briefs/gate-$1.sh" ) > "$logs/gate-$1.txt" 2>&1; local rc=$?
  tl "gate $1 $([ $rc -eq 0 ] && echo GREEN || echo RED)"; return $rc
}
gate_lines() { sed 's/\x1b\[[0-9;]*m//g' "$logs/gate-$1.txt" | grep -E 'exit|Test Files|Tests |FAIL| × |error|✖' | head -${2:-25}; }
(
  prev=
  for step in "$@"; do
    mode=new
    if [ -n "$prev" ]; then m=$(maxreq "$prev"); [ "${m:-0}" -le "${LEAN_MAX_REQ:-80000}" ] && mode=cont; fi
    run_one $mode "$step" "$briefs/$step.md" || { echo "RED $step runner did not start" > "$logs/$group.done"; exit 0; }
    { echo "===== $step ($mode, max request $(maxreq "$step") tokens): end of helper log"; tail -c "${TAILC:-1400}" "$logs/$step.log"; echo; } >> "$logs/$group.summary"
    if tail -c 3000 "$logs/$step.log" | grep -q "^STOPPED\|^NOT REPRODUCED"; then
      echo "RED $step helper ended with STOPPED / NOT REPRODUCED (see summary)" > "$logs/$group.done"; tl "group $group RED at $step"; exit 0
    fi
    if ! gate "$step"; then
      { echo "# Gate return for $step"; echo; echo "The gate for sub-task $step is RED. The lead ran it, not you. Fix the cause. Same rules and same"
        echo "files as in the brief of $step. Do not weaken a test to make it pass. A line that is in \"Known red on the"
        echo "base\" of that brief is not yours. End with \`DONE $step\` or \`STOPPED $step\` + the reason."; echo; echo '```'; gate_lines "$step" 60; echo '```'; } > "$logs/$step-r1.md"
      run_one cont "$step-r1" "$logs/$step-r1.md"
      { echo "===== $step-r1 (gate return): end of helper log"; tail -c 900 "$logs/$step-r1.log"; echo; } >> "$logs/$group.summary"
      if ! gate "$step"; then
        { echo "===== gate $step RED after 1 return"; gate_lines "$step" 40; } >> "$logs/$group.summary"
        echo "RED $step gate still red after 1 return (see gate-$step.txt)" > "$logs/$group.done"; tl "group $group RED at $step"; exit 0
      fi
    fi
    { echo "----- gate $step GREEN"; gate_lines "$step" 8; } >> "$logs/$group.summary"
    prev=$step
  done
  echo "GREEN" > "$logs/$group.done"; tl "group $group GREEN ($*)"
) </dev/null >/dev/null 2>&1 &
echo "started group $group ($*) pid $!; wait with: lean-wait.sh $logs \"$group\""
