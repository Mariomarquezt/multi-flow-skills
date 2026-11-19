#!/bin/bash
# Build a check brief with the shell. The lead writes only the head; it does not read the result back.
# usage: lean-mkcheck.sh -o <out.md> -h <head.md> -g <gate file> -d <diff file> [-i <item file>]... [-c <closed-without-change file>] [-p "<note>"]
#   -p = one line put right after the head, for a split check ("PART 1 of 2. Your items: a, b. Other files are out of scope.")
#        or a delta check ("DELTA CHECK: only this diff changed since your APPROVE. Max 8 tool calls.").
#   head.md = the top of checker-brief-standard.md, filled in, down to (not including) "## What the change must do".
#   The "What counts here" block goes in head.md too. The "Do this" + answer form come from the template.
set -u
tpl="$(cd "$(dirname "$0")/.." && pwd)/checker-brief-standard.md"
out=; head=; gate=; diff=; closed=; part=; items=()
while getopts "o:h:g:d:i:c:t:p:" f; do case $f in
  o) out=$OPTARG ;; h) head=$OPTARG ;; g) gate=$OPTARG ;; d) diff=$OPTARG ;;
  i) items+=("$OPTARG") ;; c) closed=$OPTARG ;; t) tpl=$OPTARG ;; p) part=$OPTARG ;;
  *) sed -n '2,8p' "$0"; exit 2 ;; esac; done
for v in "$out" "$head" "$gate" "$diff"; do [ -n "$v" ] || { sed -n '2,8p' "$0"; exit 2; }; done
for v in "$head" "$gate" "$diff" "$tpl" ${items[@]+"${items[@]}"} ${closed:+"$closed"}; do
  [ -s "$v" ] || { echo "lean-mkcheck: missing or empty file $v"; exit 2; }; done
{
  cat "$head"
  [ -n "$part" ] && printf '\n%s\n' "$part"
  printf '\n## What the change must do\n\n'
  for i in ${items[@]+"${items[@]}"}; do cat "$i"; printf '\n'; done
  if [ -n "$closed" ]; then printf '## Items closed WITHOUT a change\n\n'; cat "$closed"
    printf '\nDo not accept the reason because it sounds right. Is the sequence in the claim possible in this\ncode? Does the repro test follow that exact sequence, or an easier one?\n\n'; fi
  printf '## Gate output (run by the lead, not by the builder)\n\n```\n'
  sed 's/\x1b\[[0-9;]*m//g' "$gate" | grep -E 'exit|Test Files|Tests |FAIL| × |error|^#|base' | head -80
  printf '```\n\n## The diff\n\n```diff\n'
  cat "$diff"
  printf '```\n\n'
  sed -n '/^## Do this/,$p' "$tpl"
} > "$out"
wc -lc "$out"
