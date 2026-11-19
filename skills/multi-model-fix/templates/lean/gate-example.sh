#!/bin/bash
# Example of a sub-task gate, <briefs dir>/gate-<step>.sh. lean-group.sh runs it IN the worktree and
# saves all output to <logs dir>/gate-<step>.txt. Exit 0 = green. Keep it to these three parts.
# Do not use `tee /dev/stderr` or any redirect to the gate file: the caller already captures output.
export PATH=$HOME/.nvm/versions/node/v22.23.2/bin:$PATH      # the project's node, if it needs one
r=0
npx tsc --noEmit;                                  t=$?; echo "tsc exit $t";    [ $t -ne 0 ] && r=1
npx vitest run src/lib/x.test.ts 2>&1 | grep -E "FAIL| × |Test Files|Tests |Error"
                                                   v=${PIPESTATUS[0]}; echo "vitest exit $v"; [ $v -ne 0 ] && r=1
# lint: NEW errors only. BASE_ERRORS = the count on the base commit for these files (0 if clean).
BASE_ERRORS=0
e=$(npx eslint src/lib/x.ts src/lib/x.test.ts 2>&1 | grep -c " error ")
echo "eslint errors $e (base $BASE_ERRORS)";       [ "$e" -gt "$BASE_ERRORS" ] && r=1
exit $r
