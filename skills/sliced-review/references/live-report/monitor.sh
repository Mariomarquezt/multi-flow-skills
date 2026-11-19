#!/usr/bin/env bash
# monitor.sh — refresh the live sliced-review report every 4 minutes until the run ends.
#
#   monitor.sh <out-dir> ["Project title"]
#
# Each round: collect.py (on the kits host) -> pick-provider.py --providers -> haiku-check.py
# (Haiku 5.5 reads the facts, writes status.json) -> render.py -> <out-dir>/report.html.
# Env: SR_HOST   ssh host that holds the kits (default laptop; "local" = this machine)
#      SR_KITS   kits root on that host (default ~/work/sr-kits)
#      SR_APPS   comma list of app kits to show (default: the kits' apps.txt)
#      INTERVAL  seconds between rounds (default 240)
#      PUBLISH_CMD  optional command run after each render; gets the report path as $1
# Stops when <out-dir>/STOP exists, or after two rounds in a row report the run finished.
# Run it in the background from the Mac (codexbar and the claude CLI live there).
set -u
OUT="${1:?usage: monitor.sh <out-dir> [title]}"; TITLE="${2:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SR_HOST="${SR_HOST:-laptop}"; SR_KITS="${SR_KITS:-~/work/sr-kits}"; SR_APPS="${SR_APPS:-}"
INTERVAL="${INTERVAL:-240}"
mkdir -p "$OUT"
DONE_ROUNDS=0
while [ ! -e "$OUT/STOP" ]; do
  if [ "$SR_HOST" = local ]; then
    SR_KITS="$SR_KITS" SR_APPS="$SR_APPS" python3 "$HERE/collect.py" > "$OUT/snapshot.tmp" 2>"$OUT/collect.err"
  else
    ssh -o ConnectTimeout=15 "$SR_HOST" \
      "SR_KITS=$SR_KITS SR_APPS='$SR_APPS' python3 ~/.claude/skills/sliced-review/references/live-report/collect.py" \
      > "$OUT/snapshot.tmp" 2>"$OUT/collect.err"
  fi
  if [ -s "$OUT/snapshot.tmp" ]; then mv "$OUT/snapshot.tmp" "$OUT/snapshot.json"; fi
  python3 "$HERE/../pick-provider.py" --providers > "$OUT/providers.tmp" 2>/dev/null \
    && [ -s "$OUT/providers.tmp" ] && mv "$OUT/providers.tmp" "$OUT/providers.json"
  if python3 "$HERE/haiku-check.py" "$OUT/snapshot.json" "$OUT/providers.json" "$OUT/status.json"; then
    DONE_ROUNDS=$((DONE_ROUNDS + 1))
  else
    DONE_ROUNDS=0
  fi
  python3 "$HERE/render.py" "$OUT/snapshot.json" "$OUT/status.json" "$OUT/providers.json" "$OUT/report.html" "$TITLE" \
    && [ -n "${PUBLISH_CMD:-}" ] && bash -c "$PUBLISH_CMD" _ "$OUT/report.html"
  echo "[$(date '+%H:%M')] report refreshed: $OUT/report.html"
  [ "$DONE_ROUNDS" -ge 2 ] && { echo "run finished — monitor stops"; break; }
  sleep "$INTERVAL"
done
