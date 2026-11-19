#!/bin/bash
# Crouton Alpha router (owner, 11-05): spread one crouton lane over every free route that works.
# Routes + per-route caps in ~/work/sr-kits/crouton-routes.conf (lines: route=cap).
# A route that answers 429 / rate limit is put on a 10-minute cooldown (crouton-cool.<route>).
# Each run is logged to ~/work/sr-kits/crouton-route.log (time, route, rc, secs).
# Usage: crouton-route.sh "task"
K=~/work/sr-kits; CONF=$K/crouton-routes.conf; mkdir -p /tmp/crouton-sem
cmd_for(){ case $1 in
  or) echo "$HOME/.hermes/openrouter/or-free-run.sh --crouton" ;;
  oc) echo "$HOME/.hermes/opencode/oc-run.sh --model opencode/crouton-alpha-free" ;;
esac; }
while :; do
  for line in $(grep -E '^[a-z]+=[0-9]+$' "$CONF" | shuf); do
    r=${line%%=*}; cap=${line#*=}
    c=$K/crouton-cool.$r
    [ -e "$c" ] && [ $(( $(date +%s) - $(stat -c %Y "$c") )) -lt 600 ] && continue
    for k in $(seq 1 "$cap"); do
      exec 9>/tmp/crouton-sem/$r.$k
      if flock -n 9; then
        E=$(mktemp /tmp/crouton-err.XXXXXX); s=$(date +%s)
        $(cmd_for $r) "$@" 2> >(tee "$E" >&2)
        rc=$?; sleep 1
        if tail -n 30 "$E" | grep -v -E '→|Read |Grep |Glob ' | grep -qiE '(error|status|http|code)[^a-z]{0,20}[^0-9]?429([^0-9]|$)|too many requests|rate.?limit(ed)? (exceeded|reached|hit)|FreeTierError'; then touch "$c"; fi
        printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$r" "$rc" "$(( $(date +%s) - s ))" >> $K/crouton-route.log
        rm -f "$E"; exit $rc
      fi
      exec 9>&-
    done
  done
  sleep 10
done
