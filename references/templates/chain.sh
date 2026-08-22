#!/bin/bash
# Work the whole slice queue unattended, one slice at a time.
#
# Behaviour:
#   - runs ONE slice, saves its report, records its cost, THEN moves on
#   - quota window full -> waits and retries the SAME slice (never skips it)
#   - a slice that dies mid-run on a 429 is retried, not skipped, and its partial
#     output is discarded so a broken report is never recorded as done
#   - a slice that fails for any other reason is logged and skipped, so one bad
#     slice cannot stall the whole night
#   - stops on: queue empty, quota spent, MAX_HOURS elapsed, or STALL_MAX in a row
#
# Everything already finished stays on disk. Killing this script loses nothing.
set -uo pipefail
R="$(cd "$(dirname "$0")" && pwd)"
[ -f "$R/runner.env" ] && { set -a; . "$R/runner.env"; set +a; }

MAX_HOURS="${MAX_HOURS:-20}"
WAIT="${WAIT:-900}"
STOP_PCT="${STOP_PCT:-99}"
# STALL_MAX x WAIT must EXCEED one full quota window, or simply waiting for a reset
# trips it and the chain quits before the budget ever comes back.
STALL_MAX="${STALL_MAX:-26}"
STALL=0

LOG="$R/chain.log"; DONE="$R/done.txt"
touch "$DONE"; mkdir -p "$R/out"
DEADLINE=$(( $(date +%s) + MAX_HOURS*3600 ))
TOTAL=$(grep -c . "$R/queue.txt")

say() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }
pct() { [ -n "${QUOTA_PCT_CMD:-}" ] && eval "$QUOTA_PCT_CMD" 2>/dev/null; }

say "chain start — $TOTAL slices queued, deadline in ${MAX_HOURS}h"
[ -z "${QUOTA_PCT_CMD:-}" ] && say "note: backend cannot report remaining quota — a 429 is the only signal"

while read -r SLICE; do
  [ -n "$SLICE" ] || continue
  grep -qx "$SLICE" "$DONE" && { say "skip $SLICE (already done)"; continue; }

  while :; do
    if [ "$(date +%s)" -ge "$DEADLINE" ]; then say "STOP: ${MAX_HOURS}h deadline reached"; exit 0; fi
    P=$(pct)
    if [ -n "$P" ] && [ "$P" -ge "$STOP_PCT" ]; then say "STOP: quota spent at ${P}%"; exit 0; fi

    "$R/run-slice.sh" "$SLICE" >> "$LOG" 2>&1
    RC=$?

    if [ "$RC" -eq 0 ]; then
      STALL=0; echo "$SLICE" >> "$DONE"
      say "DONE $SLICE  ($(grep -c . "$DONE") of $TOTAL)"
      break
    elif [ "$RC" -eq 2 ]; then
      STALL=$((STALL+1))
      [ "$STALL" -ge "$STALL_MAX" ] && { say "STOP: quota blocked ${STALL} attempts in a row"; exit 0; }
      say "quota full (stall ${STALL}/${STALL_MAX}) — waiting ${WAIT}s, retrying $SLICE"
      sleep "$WAIT"
    elif grep -qEi '\(429\)|usage limit|quota exceeded|insufficient (credit|quota)' "$R/out/$SLICE.txt" 2>/dev/null; then
      STALL=$((STALL+1))
      # Discard BEFORE the stop check: a quota-error file left on disk reads like a report.
      rm -f "$R/out/$SLICE.txt"
      [ "$STALL" -ge "$STALL_MAX" ] && { say "STOP: 429 on ${STALL} attempts in a row (partial output discarded)"; exit 0; }
      say "$SLICE hit a 429 mid-run (stall ${STALL}/${STALL_MAX}) — discarded partial output, retrying after ${WAIT}s"
      sleep "$WAIT"
    else
      STALL=0; echo "$SLICE" >> "$DONE"
      say "$SLICE FAILED (rc=$RC), non-quota reason — skipping, output kept for inspection"
      break
    fi
  done
done < "$R/queue.txt"

say "chain finished — $(grep -c . "$DONE") of $TOTAL slices attempted"
