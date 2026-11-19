#!/usr/bin/env bash
# hb.sh <cmd...> — run cmd and print one "." to stderr every 60 s while it runs, so the idle
# watchdog (SLICE_IDLE_TIMEOUT) sees activity. Use it for backends that print nothing until they
# finish (Cursor). The hard cap SLICE_TIMEOUT still applies. Added v2.4.1 (Nova Gate test 10-23).
"$@" & c=$!
while kill -0 $c 2>/dev/null; do sleep 60; kill -0 $c 2>/dev/null && printf . >&2; done
wait $c
