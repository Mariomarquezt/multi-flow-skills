#!/bin/bash
# Wait for runs that lean-run.sh / lean-group.sh / bg-run.sh started. Returns after <max seconds>
# at most (default 230), so that a lead with a 5-minute prompt cache never waits past it.
# Call it again while it says RUNNING.
# usage: lean-wait.sh <logs dir> "<name> [<name>...]" [max seconds] [work dir for git status]
#   <name> = a step or a group. It returns when ALL names are done.
# It never uses pgrep (a pgrep pattern matches the waiting shell).
set -u
[ $# -ge 2 ] || { sed -n '2,7p' "$0"; exit 2; }
logs=$1; names=$2; max=${3:-230}; work=${4:-}
alldone() { for n in $names; do [ -f "$logs/$n.done" ] || return 1; done; }
t=0
while ! alldone && [ "$t" -lt "$max" ]; do sleep 5; t=$((t + 5)); done
rc=0
for n in $names; do
  if [ ! -f "$logs/$n.done" ]; then echo "RUNNING $n (waited ${t}s more)"; rc=3; continue; fi
  echo "DONE $n: $(cat "$logs/$n.done")"
  if [ -f "$logs/$n.summary" ]; then cat "$logs/$n.summary"
  elif [ -f "$logs/$n.log" ]; then
    echo "rate-limit lines: $(grep -ci 'rate limit\|limit will reset' "$logs/$n.log")"
    v=$(grep -m 3 "^VERDICT\|^\*\*VERDICT" "$logs/$n.log"); [ -n "$v" ] && echo "--- verdict lines" && echo "$v"
    echo "--- end of log"; tail -c "${TAILC:-1500}" "$logs/$n.log"; echo
  fi
done
[ $rc -eq 3 ] && tail -3 "$logs/timeline.txt" 2>/dev/null
if [ -n "$work" ]; then echo "--- git status"; git -C "$work" status --short; fi
exit $rc
