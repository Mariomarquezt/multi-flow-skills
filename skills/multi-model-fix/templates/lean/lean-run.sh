#!/bin/bash
# Start ONE Devin run in the background and return at once. Wait for it with lean-wait.sh.
# usage: lean-run.sh <mode> <run dir> <brief file> <logs dir> <step>
#   mode: new    = helper, fresh conversation   (--write)
#         cont   = helper, same conversation    (--write --continue; same <run dir> as before)
#         scout  = read-only reader
#         check  = read-only checker; <run dir> must NOT be the helper's worktree
#   env:  LEAN_TAG (required: the tag of the whole skill run), LEAN_HELPER (default --swe2),
#         LEAN_CHECKER (default --deepseek), LEAN_TIMEOUT (default 1500 s),
#         DEVIN_RUNNER (default $RUNNERS_DIR/devin/devin-run.sh)
# Files it writes in <logs dir>: <step>.log, <step>.pid, <step>.done (the exit code), timeline.txt
set -u
[ $# -eq 5 ] || { sed -n '2,11p' "$0"; exit 2; }
mode=$1; run_dir=$2; brief=$3; logs=$4; step=$5
: "${LEAN_TAG:?set LEAN_TAG}"
runner=${DEVIN_RUNNER:-$HOME/.hermes/devin/devin-run.sh}
case $mode in
  new)   flags="${LEAN_HELPER:---swe2} --write" ;;
  cont)  flags="${LEAN_HELPER:---swe2} --write --continue" ;;
  scout) flags="${LEAN_HELPER:---swe2}" ;;
  check) flags="${LEAN_CHECKER:---deepseek}" ;;
  *) echo "lean-run: mode must be new | cont | scout | check"; exit 2 ;;
esac
[ -d "$run_dir" ] || { echo "lean-run: no run dir $run_dir"; exit 2; }
[ -s "$brief" ] || { echo "lean-run: no brief $brief"; exit 2; }
mkdir -p "$logs"; logs=$(cd "$logs" && pwd); brief=$(cd "$(dirname "$brief")" && pwd)/$(basename "$brief")
rm -f "$logs/$step.done"
(
  cd "$run_dir" || exit 9
  echo "$(date -u +%FT%TZ) dispatch $step ($mode)" >> "$logs/timeline.txt"
  # shellcheck disable=SC2086
  DEVIN_RUN_TAG="$LEAN_TAG-$step" timeout "${LEAN_TIMEOUT:-1500}" "$runner" $flags "$(cat "$brief")" > "$logs/$step.log" 2>&1
  rc=$?
  echo "$(date -u +%FT%TZ) $step end rc=$rc" >> "$logs/timeline.txt"
  echo "$rc" > "$logs/$step.done"
) </dev/null >/dev/null 2>&1 &
echo $! > "$logs/$step.pid"
echo "started $step ($mode) pid $(cat "$logs/$step.pid"); wait with: lean-wait.sh $logs $step"
