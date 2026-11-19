#!/usr/bin/env bash
# lane.sh <app> <lane>  — run one model ("lane") through one app's slice queue, one slice at a time.
# Many lanes run at once (one lane.sh per model); they share the queue by an atomic claim file.
# Kits root = $SR_KITS (default ~/work/sr-kits): lanes.tsv, slots.conf, alias.tsv, <app>/{WORKDIR,
# _context.md, slices/, queue.txt}. Per-provider concurrency is capped by slots.conf (re-read before
# every slice). Watchdog: idle timeout + hard cap, kills the whole process group.
# Results: <app>/out/<lane>/<slice>.md (a report counts only if it ends with "TOTAL FINDINGS: <n>").
# Ledger: <app>/ledger.tsv (time, lane, provider, model, slice, status, secs, bytes, tokens).
# Stop:  touch $SR_KITS/STOP (all), STOP.<provider>, STOP.lane.<lane>, or <app>/STOP.<lane>.
# Drain: touch DRAIN.lane.<lane> or DRAIN.<provider> = finish the current slice, start no new one.
# Env: MAX_SLICES=<n> stop after n good slices; ONLY=<slice> one slice; REV=1 queue in reverse;
#      MAX_PASSES=<n> retry passes (default 6). Linux (setsid, flock); runs on the laptop.
set -u
APP="$1"; LANE="$2"
K="${SR_KITS:-$HOME/work/sr-kits}"; A="$K/$APP"
USAGE_PY="$HOME/.claude/skills/sliced-review/references/templates/usage.py"
[ -f "$USAGE_PY" ] || USAGE_PY="$K/tools/usage.py"
LINE="$(awk -F'\t' -v l="$LANE" '$1==l' "$K/lanes.tsv")"
[ -n "$LINE" ] || { echo "lane.sh: unknown lane $LANE" >&2; exit 2; }
PROV="$(cut -f2 <<<"$LINE")"; MODEL="$(cut -f3 <<<"$LINE")"; CMD_T="$(cut -f4- <<<"$LINE")"
WORKDIR="$(cat "$A/WORKDIR")"
# alias.tsv: "<lane>\t<shared out name>" lets two routes of ONE model split the same slices (e.g. Grok on xAI + Cursor).
OUTL="$(awk -F'\t' -v l="$LANE" '$1==l{print $2}' "$K/alias.tsv" 2>/dev/null)"; OUTL="${OUTL:-$LANE}"
OUT="$A/out/$OUTL"; mkdir -p "$OUT" /tmp/sr-sem
LEDGER="$A/ledger.tsv"
[ -f "$LEDGER" ] || printf 'ts\tapp\tlane\tprovider\tmodel\tslice\tstatus\tsecs\tbytes\tusage\n' > "$LEDGER"
case "$PROV" in codex|claude|cmd) IDLE=2400 ;; *) IDLE=900 ;; esac
HARD=3000
MAX_SLICES="${MAX_SLICES:-0}"; DONE_N=0

slots() { awk -F= -v p="$PROV" '$1==p{print $2}' "$K/slots.conf" | tail -1; }
stopflag() { [ -e "$K/STOP" ] || [ -e "$K/STOP.$PROV" ] || [ -e "$A/STOP.$LANE" ] || [ -e "$K/STOP.lane.$LANE" ]; }

drainflag() { [ -e "$K/DRAIN.lane.$LANE" ] || [ -e "$K/DRAIN.$PROV" ]; }   # finish the current slice, start no new one
acquire() {  # sets SEM_FD
  while true; do
    stopflag && return 1
    drainflag && return 1
    local n; n="$(slots)"; n="${n:-1}"
    for k in $(seq 1 "$n"); do
      exec {SEM_FD}>"/tmp/sr-sem/$PROV.$k"
      if flock -n "$SEM_FD"; then SLOTK=$k; return 0; fi
      exec {SEM_FD}>&-
    done
    sleep 15
  done
}

run_one() {  # $1 slice → 0 ok, 1 fail, 75 quota
  local S="$1" P T RAW ERR start last sz psz now pid status
  P="$(mktemp /tmp/sr-prompt.XXXXXX)"; T="$(mktemp /tmp/sr-t.XXXXXX)"
  cat "$A/_context.md" "$A/slices/$S.md" > "$P"
  RAW="$OUT/$S.raw"; ERR="$OUT/$S.err"
  local CMD="${CMD_T//\{P\}/$P}"; CMD="${CMD//\{T\}/$T}"; CMD="${CMD//\{APP\}/$APP}"
  # Devin: one private checkout per slot, so --continue only ever sees this slot's own conversation.
  RUNDIR="$WORKDIR"
  if [ "$PROV" = devin ]; then
    RUNDIR="${WORKDIR}.dev${SLOTK}"
    if [ ! -d "$RUNDIR" ]; then
      if git -C "$WORKDIR" rev-parse --git-dir >/dev/null 2>&1; then git -C "$WORKDIR" worktree add -q --detach "$RUNDIR" HEAD >/dev/null 2>&1 || cp -a "$WORKDIR" "$RUNDIR"
      else cp -a "$WORKDIR" "$RUNDIR"; fi
    fi
  fi
  start=$(date +%s); last=$start; psz=-1
  ( cd "$RUNDIR" && exec setsid bash -c "$CMD" ) > "$RAW" 2> "$ERR" < /dev/null &
  pid=$!
  status=""
  while kill -0 "$pid" 2>/dev/null; do
    sleep 10; now=$(date +%s)
    sz=$(( $(stat -c %s "$RAW" 2>/dev/null || echo 0) + $(stat -c %s "$ERR" 2>/dev/null || echo 0) ))
    [ "$sz" != "$psz" ] && { last=$now; psz=$sz; }
    if [ $((now-last)) -gt "$IDLE" ]; then status=KILLED_IDLE; fi
    if [ $((now-start)) -gt "$HARD" ]; then status=KILLED_TIMECAP; fi
    if stopflag; then status=STOPPED; fi
    if [ -n "$status" ]; then
      local pg; pg="$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')"
      [ -n "$pg" ] && kill -TERM -- "-$pg" 2>/dev/null; sleep 5; [ -n "$pg" ] && kill -KILL -- "-$pg" 2>/dev/null
      break
    fi
  done
  wait "$pid" 2>/dev/null; local rc=$?
  # Devin early stop: it narrates "now I will read X" and ends. Continue the same conversation, up to 3 times.
  if [ -z "$status" ] && [ "$PROV" = devin ]; then
    local C="$P.cont" n=0
    printf '%s\n' "Continue the review you started. Read any remaining files of the slice, then write ALL your findings (severity, file:line, what is wrong, failure scenario). Do not narrate; call tools until you are ready, then write the full report. End with the line: TOTAL FINDINGS: <n>" > "$C"
    local CC="${CMD_T//\"\$(cat \{P\})\"/--continue \"\$(cat \{P\})\"}"; CC="${CC//\{P\}/$C}"; CC="${CC//\{APP\}/$APP}"
    while [ $n -lt 3 ] && ! tail -n 25 "$RAW" | grep -qE 'TOTAL FINDINGS:? *[0-9]+'; do
      tail -n 20 "$RAW" "$ERR" 2>/dev/null | grep -qiE 'rate.?limit|usage limit|quota|out of credits|upgrade to pro' && break
      printf '\n\n--- continue %s ---\n' "$((n+1))" >> "$RAW"
      ( cd "$RUNDIR" && exec setsid timeout "$HARD" bash -c "$CC" ) >> "$RAW" 2>> "$ERR" < /dev/null
      n=$((n+1))
    done
    rm -f "$C"
  fi
  local secs=$(( $(date +%s) - start )) bytes; bytes=$(stat -c %s "$RAW" 2>/dev/null || echo 0)
  local usage; usage="$(grep -hE 'usage:|in=|cost|tokens' "$ERR" 2>/dev/null | tail -1 | tr '\t' ' ' | cut -c1-300)"
  # Token capture (usage.py): fills runs whose runner prints no usage line (codex, cursor, opencode, xai, cmd)
  # and sums Devin's --continue runs. Line: `tokens: in=.. cached=.. cache_write=.. out=.. source=.. api_usd=..`.
  if [ "$PROV" = devin ] || ! grep -qE '(^| )out=[0-9]+' <<<"$usage"; then
    local rm cap; rm="$(grep -oE -- '--model [^ ]+' <<<"$CMD_T" | head -1 | cut -d' ' -f2 | tr -d '"')"
    cap="$(timeout 90 python3 "$USAGE_PY" capture --provider "$PROV" --model "$MODEL" --runner-model "$rm" \
           --cwd "$RUNDIR" --start "$start" --end "$(date +%s)" --err "$ERR" 2>/dev/null | tail -1 | tr '\t' ' ' | cut -c1-300)"
    case "$cap" in "tokens: in="*) usage="$cap" ;; esac
  fi
  local ret=1
  if [ -z "$status" ]; then
    if tail -n 25 "$RAW" | grep -qE 'TOTAL FINDINGS:? *[0-9]+'; then
      status=OK; mv "$RAW" "$OUT/$S.md"; ret=0
    elif tail -n 20 "$RAW" "$ERR" 2>/dev/null | grep -qiE '(^|[^0-9])429([^0-9]|$)|rate.?limit|usage limit|quota|out of credits|insufficient credit|exceeded your|limit reached|reached your [0-9a-z -]*limit|upgrade to pro'; then
      status=QUOTA; ret=75
    else
      status="FAIL_rc$rc"
    fi
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -Is)" "$APP" "$LANE" "$PROV" "$MODEL" "$S" "$status" "$secs" "$bytes" "$usage" >> "$LEDGER"
  rm -f "$P" "$T" "$T".*
  return $ret
}

QWAITS=0
for PASS in $(seq 1 ${MAX_PASSES:-6}); do  # MAX_PASSES env (10-18): fewer retry passes for flaky lanes
 for S in $(if [ -n "${ONLY:-}" ]; then echo "$ONLY"; elif [ -n "${REV:-}" ]; then tac "$A/queue.txt"; else cat "$A/queue.txt"; fi); do
  [ -s "$OUT/$S.md" ] && continue
  # Atomic claim (10-24): noclobber makes the create fail if another process already made the file.
  # A claim whose owner PID is dead (killed lane) is stale: remove it and try once more.
  if ! ( set -o noclobber; echo $$ > "$OUT/$S.claimed" ) 2>/dev/null; then
    owner=$(cat "$OUT/$S.claimed" 2>/dev/null)
    if [ -n "$owner" ] && ! kill -0 "$owner" 2>/dev/null; then
      rm -f "$OUT/$S.claimed"
      ( set -o noclobber; echo $$ > "$OUT/$S.claimed" ) 2>/dev/null || continue
    else
      continue                                    # another live process of this lane took it
    fi
  fi
  [ -s "$OUT/$S.md" ] && { rm -f "$OUT/$S.claimed"; continue; }   # finished between check and claim
  tries=0
  while [ $tries -lt 2 ]; do
    acquire || { rm -f "$OUT/$S.claimed"; echo "lane $LANE: stop flag"; exit 0; }
    run_one "$S"; r=$?
    exec {SEM_FD}>&-
    [ $r -eq 0 ] && break
    if [ $r -eq 75 ]; then
      QWAITS=$((QWAITS+1))
      if [ $QWAITS -gt 8 ]; then rm -f "$OUT/$S.claimed"; echo "lane $LANE: QUOTA 8 waits — lane stopped"; touch "$A/STOP.$LANE"; date -Is > "$K/QUOTA.$LANE"; exit 75; fi
      echo "lane $LANE: quota at $S, wait $QWAITS/8 (15 min)"; sleep 900; continue
    fi
    tries=$((tries+1)); sleep 20
  done
  rm -f "$OUT/$S.claimed"
  if [ -s "$OUT/$S.md" ]; then DONE_N=$((DONE_N+1)); fi
  if [ "$MAX_SLICES" -gt 0 ] && [ "$DONE_N" -ge "$MAX_SLICES" ]; then echo "lane $LANE: reached MAX_SLICES=$MAX_SLICES"; exit 0; fi
 done
 left=0; for S in $(cat "$A/queue.txt"); do [ -s "$OUT/$S.md" ] || [ -e "$OUT/$S.claimed" ] || left=$((left+1)); done
 [ $left -eq 0 ] && break
 [ -n "${ONLY:-}" ] && break
 echo "lane $LANE: pass $PASS left $left slices undone; next pass in 2 min"; sleep 120
done
echo "lane $LANE: queue done for $APP"
