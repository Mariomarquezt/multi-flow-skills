#!/bin/bash
# Bring the changes of all helper worktrees into ONE tree (the check / integration tree) and
# write the complete diff. The full gate and the checker run in that tree, never in a helper's.
# usage: lean-collect.sh <integration dir> <out.patch> <helper worktree> [<helper worktree>...]
#   The integration tree is at the BASE commit. A helper tree is at the base, or at ONE seam commit
#   after it (the seam is then applied one time, so <out.patch> is the complete diff against the base). The integration tree is RESET first (git reset --hard,
#   git clean -fd: ignored files such as node_modules stay). Helper trees: `git add -A` only.
#   A second call after a fix round also writes <out.patch>.delta = what changed since the last call.
set -u
[ $# -ge 3 ] || { sed -n '2,9p' "$0"; exit 2; }
int=$1; out=$2; shift 2
git -C "$int" reset -q --hard HEAD && git -C "$int" clean -q -fd || exit 9
: > "$out.delta.tmp"
seam=
for wt in "$@"; do
  ih=$(git -C "$int" rev-parse HEAD); wh=$(git -C "$wt" rev-parse HEAD)
  if [ "$wh" != "$ih" ]; then   # the helper tree sits on a seam commit made after the integration tree's commit
    git -C "$wt" merge-base --is-ancestor "$ih" "$wh" || { echo "lean-collect: $wt is not at, or after, the commit of $int"; exit 9; }
    if [ "$seam" != "$wh" ]; then
      [ -z "$seam" ] || { echo "lean-collect: two different seam commits ($seam, $wh)"; exit 9; }
      git -C "$wt" diff --binary "$ih" "$wh" | git -C "$int" apply --index - || { echo "lean-collect: the seam commit of $wt does not apply"; exit 9; }
      seam=$wh
    fi
  fi
  if ! git -C "$wt" diff --cached --quiet HEAD; then git -C "$wt" add -A -N . ; git -C "$wt" diff --binary >> "$out.delta.tmp"; fi
  git -C "$wt" add -A . || exit 9
  if ! git -C "$wt" diff --cached --quiet HEAD; then
    git -C "$wt" diff --cached --binary HEAD | git -C "$int" apply --index - || { echo "lean-collect: the diff of $wt does not apply (two groups edited the same file?)"; exit 9; }
  fi
done
git -C "$int" diff --cached --binary HEAD > "$out"
if [ -s "$out.delta.tmp" ]; then mv "$out.delta.tmp" "$out.delta"; echo "delta since the last collect: $(grep -c '^[+-][^+-]' "$out.delta") changed lines -> $out.delta"; else rm -f "$out.delta.tmp"; fi
git -C "$int" diff --cached --stat HEAD | tail -4
echo "changed lines: $(grep -c '^[+-][^+-]' "$out")  -> $out"
