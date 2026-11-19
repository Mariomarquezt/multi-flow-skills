#!/bin/bash
# OpenRouter FREE models only, through OpenCode (oc-run.sh). Added 2026-11-05 for the repo owner.
# The owner approved OpenRouter for free models by name (Crouton Alpha, 2026-11-05).
# Guard: before every run, ask OpenRouter's public model list for the price.
# If prompt or completion price is not exactly 0, refuse (exit 3). No money ever.
# Usage: or-free-run.sh --model <openrouter-model-id> [oc-run.sh args...] "task"
#   or-free-run.sh --crouton "task"   (= stealth/crouton-alpha)
set -euo pipefail
M=""
case "${1:-}" in
  --crouton) M="stealth/crouton-alpha"; shift ;;
  --model) M="${2:?--model needs an id}"; shift 2 ;;
esac
[ -n "$M" ] || { echo "or-free-run: give --crouton or --model <id>" >&2; exit 2; }
P=$(curl -s --max-time 30 https://openrouter.ai/api/v1/models | python3 -c '
import json,sys
m=sys.argv[1]
d=json.load(sys.stdin)["data"]
r=[x for x in d if x["id"]==m]
if not r: print("MISSING"); sys.exit()
p=r[0]["pricing"]
print("FREE" if float(p.get("prompt") or 1)==0 and float(p.get("completion") or 1)==0 and float(p.get("request") or 0)==0 else "PAID")
' "$M" 2>/dev/null || echo ERROR)
[ "$P" = FREE ] || { echo "or-free-run: $M price check = $P; refusing (free models only)" >&2; exit 3; }
set -a; . "$HOME/.hermes/secrets/openrouter.env"; set +a
exec "$HOME/.hermes/opencode/oc-run.sh" --model "openrouter/$M" "$@"
