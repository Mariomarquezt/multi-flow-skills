#!/usr/bin/env bash
# critic.sh <arm> <prompt-file> <out-file>
# Run ONE critic model, read-only, on a plan brief. Writes the critic's final answer to <out-file>
# and the raw transcript to <out-file>.transcript. Prints "<arm> <provider> exit=<n> secs=<s>".
# Arms: sol | grok | composer | deepseek | glm | minimax | qwen | mimo
# Multi-provider arms ask pick-provider.py for the provider whose tokens expire first.
# Override with PROVIDER=<key>. Never routes to OpenRouter.
set -uo pipefail
arm="$1"; prompt_file="$2"; out="$3"
REF="$HOME/.claude/skills/sliced-review/references"
HB="$REF/templates/hb.sh"
H="$HOME/.hermes"
prompt="$(cat "$prompt_file")"
start=$(date +%s)

pick() { # $1 = model short name in models.md
  [ -n "${PROVIDER:-}" ] && { echo "$PROVIDER"; return; }
  timeout 90 python3 "$REF/pick-provider.py" --model "$1" 2>/dev/null | tail -1 | tr -d '[:space:]'
}

provider=""
case "$arm" in
  sol)
    provider=codex
    SOL_ID="$(grep -m1 '^| \*\*Sol\*\*' "$HOME/.claude/skills/_shared/models.md" | awk -F'`' '{print $2}')"  # id lives in _shared/models.md
    T="$(mktemp)"
    codex exec --skip-git-repo-check -m "${SOL_ID:-gpt-6.2-sol}" -c model_reasoning_effort="high" \
      -s read-only -o "$T" "$prompt" < /dev/null > "$out.transcript" 2>&1
    rc=$?; cat "$T" > "$out"; rm -f "$T" ;;
  grok)
    provider=cursor
    "$HB" "$H/cursor/cursor-run.sh" --model cursor-grok-4.6-high "$prompt" < /dev/null > "$out" 2> "$out.transcript"
    rc=$? ;;
  composer)
    provider=cursor
    "$HB" "$H/cursor/cursor-run.sh" --model composer-2.5 "$prompt" < /dev/null > "$out" 2> "$out.transcript"
    rc=$? ;;
  minimax)
    provider=opencodego
    "$H/opencode/oc-run.sh" --model opencode-go/minimax-m3.1-flash "$prompt" < /dev/null > "$out" 2> "$out.transcript"
    rc=$? ;;
  deepseek|glm|qwen|mimo)
    case "$arm" in
      deepseek) name="DeepSeek Flash"; pi=--deepseek;   cmdm=deepseek-v4.1-flash; cl=--deepseek;   dv=--deepseek ;;
      glm)      name="GLM Flash";      pi=--glm;        cmdm=glm-5.3-flash;       cl=--glm-flash;  dv=--glm ;;
      qwen)     name="Qwen Flash";     pi=--qwen-flash; cmdm=qwen3.8-flash;       cl="";           dv="" ;;
      mimo)     name="MiMo Flash";     pi=--mimo-flash; cmdm=mimo-v2.6-flash;     cl=--mimo-flash; dv="" ;;
    esac
    provider="$(pick "$name")"
    # devin is paid per run: only when the user set PROVIDER=devin themselves.
    if [ "$provider" = devin ] && [ "${PROVIDER:-}" != devin ]; then provider=opencodego; fi
    [ -z "$provider" ] && provider=opencodego
    case "$provider" in
      opencodego) "$H/pi/pi-run.sh" $pi "$prompt" < /dev/null > "$out" 2> "$out.transcript"; rc=$?
                  if [ $rc -ne 0 ] || [ ! -s "$out" ]; then   # Pi failed: same task on OpenCode backup
                    "$H/opencode/oc-run.sh" $pi "$prompt" < /dev/null > "$out" 2>> "$out.transcript"; rc=$?
                    provider=opencodego-oc; fi ;;
      cmd)   "$H/cmd/cmd-run.sh" --model "$cmdm" "$prompt" < /dev/null > "$out" 2> "$out.transcript"; rc=$? ;;
      cline) [ -z "$cl" ] && { echo "no cline route for $arm" >&2; exit 2; }
             "$H/cline/cline-run.sh" $cl "$prompt" < /dev/null > "$out" 2> "$out.transcript"; rc=$? ;;
      devin) [ -z "$dv" ] && { echo "no devin route for $arm" >&2; exit 2; }
             "$H/devin/devin-run.sh" $dv "$prompt" < /dev/null > "$out" 2> "$out.transcript"; rc=$? ;;
      *) echo "unknown provider '$provider' for $arm" >&2; exit 2 ;;
    esac
    # Last resort when the picked plan is full or down: Command Code, same model.
    if { [ "${rc:-1}" -ne 0 ] || [ ! -s "$out" ]; } && [ "${provider#cmd}" = "$provider" ]; then
      echo "critic: $provider failed, retrying on cmd" >> "$out.transcript"
      "$H/cmd/cmd-run.sh" --model "$cmdm" "$prompt" < /dev/null > "$out" 2>> "$out.transcript"; rc=$?
      provider="cmd(fallback)"
    fi ;;
  *) echo "unknown arm '$arm' (sol|grok|composer|deepseek|glm|minimax|qwen|mimo)" >&2; exit 2 ;;
esac

[ -s "$out" ] || rc=${rc:-1}
echo "$arm $provider exit=${rc:-0} secs=$(( $(date +%s) - start )) bytes=$(wc -c < "$out" | tr -d ' ')"
exit "${rc:-0}"
