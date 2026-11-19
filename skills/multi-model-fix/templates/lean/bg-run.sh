#!/bin/bash
# Start ANY long command in the background and return at once. Wait for it with lean-wait.sh.
# usage: bg-run.sh <logs dir> <step> -- <command> [args...]
#   example: bg-run.sh ~/work/x-logs review1 -- codex exec -s read-only -o out.md "$(cat brief.md)"
# The command runs in the current directory. Files in <logs dir>: <step>.log, <step>.pid,
# <step>.done (the exit code), timeline.txt. For Devin runs use lean-run.sh (it sets the tag).
set -u
[ $# -ge 4 ] && [ "$3" = "--" ] || { sed -n '2,6p' "$0"; exit 2; }
logs=$1; step=$2; shift 3
mkdir -p "$logs"; logs=$(cd "$logs" && pwd); rm -f "$logs/$step.done"
(
  echo "$(date -u +%FT%TZ) dispatch $step" >> "$logs/timeline.txt"
  "$@" > "$logs/$step.log" 2>&1
  rc=$?
  echo "$(date -u +%FT%TZ) $step end rc=$rc" >> "$logs/timeline.txt"
  echo "$rc" > "$logs/$step.done"
) </dev/null >/dev/null 2>&1 &
echo $! > "$logs/$step.pid"
echo "started $step pid $(cat "$logs/$step.pid"); wait with: lean-wait.sh $logs $step"
