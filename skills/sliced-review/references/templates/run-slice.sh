#!/bin/bash
# Run ONE review slice, with an optional quota guard, a cost ledger and a token ledger.
# Usage: run-slice.sh <slice-name>
#
# NEVER run two of these at the same time. Parallel whole-repo lanes are what emptied a
# weekly subscription in nine minutes for zero findings (see the skill's FIELD-NOTES.md);
# smaller slices do not make parallelism safe, they just make the waste finer-grained.
#
# The prompt is written to a TEMP FILE and RUNNER_CMD references it as {PROMPT_FILE}.
# The prompt text is never substituted into the command string: slice briefs are full of
# backticks and $(...) and eval would execute them.
#
# Backend config lives in runner.env beside this script. If QUOTA_PCT_CMD is empty there,
# THERE IS NO PRE-FLIGHT CHECK — a 429 is the only out-of-quota signal. Say so out loud
# rather than letting a reader assume a guard exists.
set -uo pipefail
R="$(cd "$(dirname "$0")" && pwd)"
[ -f "$R/runner.env" ] || { echo "run-slice: missing $R/runner.env"; exit 1; }
# shellcheck disable=SC1091
set -a; . "$R/runner.env"; set +a
: "${RUNNER_CMD:?runner.env must set RUNNER_CMD}"
: "${MAX_PCT:=60}"
REPO="${REPO:-$(cd "$R/../.." && pwd)}"

SLICE="${1:-}"
if [ -z "$SLICE" ]; then
  echo "usage: run-slice.sh <slice-name>"; ls "$R/slices" 2>/dev/null | sed 's/\.md$//'; exit 1
fi
F="$R/slices/$SLICE.md"
[ -f "$F" ] || { echo "no such slice: $SLICE"; ls "$R/slices" | sed 's/\.md$//'; exit 1; }

pct() { [ -n "${QUOTA_PCT_CMD:-}" ] && eval "$QUOTA_PCT_CMD" 2>/dev/null; }

BEFORE=$(pct); BEFORE=${BEFORE:-unknown}
if [ "$BEFORE" = "unknown" ]; then
  echo "[$(date '+%H:%M:%S')] quota before — unknown (backend cannot report remaining quota)"
else
  echo "[$(date '+%H:%M:%S')] quota before — ${BEFORE}% used"
  if [ "$BEFORE" -ge "$MAX_PCT" ]; then
    echo "ABORT: already at ${BEFORE}% (limit ${MAX_PCT}%). Wait for the reset."; exit 2
  fi
fi

COST_BEFORE=""
[ -n "${COST_BEFORE_CMD:-}" ] && COST_BEFORE=$(eval "$COST_BEFORE_CMD" 2>/dev/null | tr -d '\n' | cut -c1-60)

mkdir -p "$R/out"
OUT="$R/out/$SLICE.txt"
PROMPT_FILE="$(mktemp "${TMPDIR:-/tmp}/slice-prompt.XXXXXX")"
trap 'rm -f "$PROMPT_FILE"' EXIT
{ cat "$R/_context.md"; echo; cat "$F"; } > "$PROMPT_FILE"

echo "[$(date '+%H:%M:%S')] running $SLICE ..."
STARTED=$(date +%s)
cd "$REPO" || exit 1
CMD="${RUNNER_CMD//\{PROMPT_FILE\}/$PROMPT_FILE}"
# WATCHDOG — do not remove this, and do not write a driver loop without one.
#
# A backend that fails by HANGING is the most expensive failure mode there is. It never errors, so
# nothing alerts, no retry fires, and the meter keeps running. Measured 2026-08-17: qwen3.8-max sat
# on ONE slice for 19h37m, produced 32 bytes (its banner line and nothing else), and the provider's
# cost counter rose ~$9.94 in that window. It had already hung once at a different reasoning
# variant. Neither run ever returned an error.
#
# TWO LIMITS, because they answer different questions:
#
#   SLICE_IDLE_TIMEOUT (default 600s) — kills a run that has written NOTHING NEW for this long.
#     This is the real hang detector, and it is activity-aware: a backend that is still streaming
#     tool calls or report text keeps resetting the clock and is never touched, however long it
#     takes. The qwen hang wrote its banner and then nothing for 19 hours; this catches that in ten
#     minutes without endangering a slow-but-working run.
#
#   SLICE_TIMEOUT (default 1200s / 20 min) — absolute backstop, regardless of activity. For a
#     backend that emits steady noise while making no progress, which idle detection cannot see.
#
# HONEST LIMIT OF THE IDLE CHECK: a backend that BUFFERS all its output and writes one block at the
# end is indistinguishable from a hang while it works. None of the measured backends do this — codex
# and opencode both stream — but if you wire one that does, raise SLICE_IDLE_TIMEOUT above its
# expected runtime or set it to 0 to disable idle detection and rely on the hard cap alone.
#
# macOS ships no coreutils `timeout`, hence the hand-rolled watchdog.
#
# Subshell on purpose: eval runs in the CURRENT shell, so a backend command that calls
# exit (or sets variables, or traps) would otherwise kill this runner mid-slice and no
# ledger line would ever be written.
( eval "$CMD" ) > "$OUT" 2>&1 < /dev/null &
CMD_PID=$!
KILLED_MARK="$(mktemp "${TMPDIR:-/tmp}/slice-killed.XXXXXX")"; rm -f "$KILLED_MARK"
( DEADLINE=$(( $(date +%s) + ${SLICE_TIMEOUT:-1200} ))
  IDLE=${SLICE_IDLE_TIMEOUT:-600}
  LAST_SIZE=-1; LAST_CHANGE=$(date +%s)
  while kill -0 "$CMD_PID" 2>/dev/null; do
    SIZE=$(wc -c < "$OUT" 2>/dev/null | tr -d ' '); SIZE=${SIZE:-0}
    # Any growth at all means the backend is still producing. Reset the idle clock and leave it be,
    # however long it has been running.
    if [ "$SIZE" != "$LAST_SIZE" ]; then LAST_SIZE=$SIZE; LAST_CHANGE=$(date +%s); fi
    NOW=$(date +%s)
    if { [ "$IDLE" -gt 0 ] && [ $(( NOW - LAST_CHANGE )) -ge "$IDLE" ]; } || [ "$NOW" -ge "$DEADLINE" ]; then
      # Kill the process GROUP. These backends spawn node/python children that survive a bare
      # kill on the wrapper and would carry on billing, unparented and invisible.
      [ $(( NOW - LAST_CHANGE )) -ge "$IDLE" ] && echo idle > "$KILLED_MARK" || echo cap > "$KILLED_MARK"
      pkill -P "$CMD_PID" 2>/dev/null; kill -9 "$CMD_PID" 2>/dev/null
      exit 0
    fi
    sleep 10
  done ) &
WATCHDOG=$!
wait "$CMD_PID" 2>/dev/null
RC=$?
kill "$WATCHDOG" 2>/dev/null

ELAPSED=$(( $(date +%s) - STARTED ))
AFTER=$(pct); AFTER=${AFTER:-unknown}
BYTES=$(wc -c < "$OUT" | tr -d ' ')
COST=""
[ -n "${COST_CMD:-}" ] && COST=$(eval "$COST_CMD" 2>/dev/null | tr '\n' ' ' | cut -c1-160)
# Some backends report only a CUMULATIVE, all-time spend and have no per-run view at all. For
# those, set COST_BEFORE_CMD as well: the delta between the two readings is the slice's real cost.
[ -n "$COST_BEFORE" ] && COST="${COST_BEFORE} -> ${COST}"

# TOKENS + API-EQUIVALENT COST — recorded for EVERY run, flat plan or free model included.
# usage.py reads the backend's own record (claude/cline/devin stderr line, opencode.db, ~/.codex/sessions,
# $RUNNERS_DIR/cursor/usage.jsonl, ~/.commandcode/projects) and prices it: prices.json -> the runner's own
# table -> OpenRouter's public price list. `unknown` when no price is found; never an invented one.
# USAGE_PROVIDER / USAGE_MODEL in runner.env; when unset they are guessed from RUNNER_CMD.
USAGE_PY="${USAGE_PY:-$HOME/.claude/skills/sliced-review/references/templates/usage.py}"
UP="${USAGE_PROVIDER:-}"
if [ -z "$UP" ]; then
  case "$RUNNER_CMD" in
    *codex\ exec*) UP=codex ;; *claude\ -p*) UP=claude ;; *cesego-run*) UP=cesego ;; *xai-run*) UP=xai ;;
    *oc-run*|*opencode\ run*|*mimo-run*|*nexum-run*) UP=oc ;; *cursor-run*|*cursor-agent*) UP=cursor ;;
    *devin-run*) UP=devin ;; *cline-run*) UP=cline ;; *cmd-run*|*/cmd\ *) UP=cmd ;;
  esac
fi
UM="${USAGE_MODEL:-$(grep -oE -- '(--model|-m) [^ ]+' <<<"$RUNNER_CMD" | head -1 | cut -d' ' -f2 | tr -d '"'"'"'"')}"
TOKENS="unknown"; API_USD="unknown"
if [ -n "$UP" ] && [ -f "$USAGE_PY" ]; then
  CAP=$(python3 "$USAGE_PY" capture --provider "$UP" --model "${UM:-unknown}" --cwd "$REPO" \
        --start "$STARTED" --end "$(date +%s)" --err "$OUT" 2>/dev/null | tail -1)
  case "$CAP" in
    "tokens: in="*) TOKENS=$(sed -E 's/^tokens: (in=[0-9]+ cached=[0-9]+ cache_write=[0-9]+ out=[0-9]+).*/\1/' <<<"$CAP")
                    API_USD=$(grep -oE 'api_usd=[^ ]+' <<<"$CAP" | cut -d= -f2) ;;
    *) TOKENS="none($(grep -oE 'source=[^=]*' <<<"$CAP" | sed 's/source=//; s/ api_usd$//'))" ;;
  esac
else
  TOKENS="none(set USAGE_PROVIDER in runner.env)"
fi

# A quota error is a DISCARDED run, never a completed one.
STATUS=OK
grep -qEi '\(429\)|usage limit|quota exceeded|rate.?limit(ed)? exceeded|insufficient (credit|quota)' "$OUT" && STATUS=QUOTA_429
[ "$RC" -ne 0 ] && [ "$STATUS" = OK ] && STATUS="EXIT_$RC"
[ "$BYTES" -lt 1500 ] && [ "$STATUS" = OK ] && STATUS=SUSPICIOUSLY_SHORT
# A watchdog kill reads as an ordinary signal death, which would otherwise be filed as EXIT_137 and
# look like a backend crash. The marker file says which limit fired, so a hang is never mistaken for
# a report and never reaches done.txt as a finished slice.
if [ -s "$KILLED_MARK" ]; then
  [ "$(cat "$KILLED_MARK")" = idle ] && STATUS=KILLED_IDLE || STATUS=KILLED_TIMECAP
fi
rm -f "$KILLED_MARK"

# Columns: date, slice, quota before->after, bytes, time, status, cost, tokens, api_usd (last two added 2026-10-15).
printf '%s\t%s\t%s->%s\t%s bytes\t%dm%02ds\t%s\t%s\t%s\t%s\n' \
  "$(date '+%Y-%m-%d %H:%M')" "$SLICE" "$BEFORE" "$AFTER" "$BYTES" \
  "$((ELAPSED/60))" "$((ELAPSED%60))" "$STATUS" "$COST" "$TOKENS" "$API_USD" \
  >> "$R/ledger.tsv"

echo "[$(date '+%H:%M:%S')] $SLICE -> $STATUS"
echo "  quota after — ${AFTER}${AFTER:+%} used"
echo "  output: $OUT ($BYTES bytes, $((ELAPSED/60))m$((ELAPSED%60))s)"
[ -n "$COST" ] && echo "  cost: $COST"
echo "  tokens: $TOKENS  api_usd: $API_USD"
[ "$STATUS" = OK ] || exit 3
