# Lean lane + run rules (multi-fix, multi-build)

Added 2026-10-08 (the user approved). Source: Devin "Fusion" (a cheap model reads and does the
hands-on work, the lead model plans and gives small sub-tasks) plus what the 2026-10-07 two client
Swift-app runs showed. Both skills point here. Go back to the old skills: `git checkout
pre-lean-2026-10-08 -- multi-model-fix multi-build` in `~/.claude/skills`.

Two parts:

- **Part A, run rules.** They apply in EVERY mode (`2`, `3`, `5`, `fast`, `lean`). A6 (keep the
  prompt cache warm) applies to every skill that waits for a long run.
- **Part B, the `lean` mode.** One helper model, short briefs, groups on autopilot. An added lane, not a
  replacement: different models still find more defects than one helper.

---

## Part A — run rules for every mode

### A1. Size router (say the lane in the one-line mode statement)

Count the queued items and the files they touch after the verify / split step.

| job | lane |
|---|---|
| separate defects: 1 to 6 items, 8 files or fewer, no shared first part | `lean` |
| a feature with a shared first part (a seam that the other parts need) | `3` or `5` (regular) |
| more than 6 items or 8 files | `3` or `5` (regular) |
| security, money, data migration, auth | regular, never `lean` (more eyes) |

**Short form (the user 2026-10-08): separate defects = `lean`; a feature with a shared first part =
regular.** Measured on 2 jobs: on 4 separate defects `lean` took 20.6 min and $3.71, regular 29 min
and $5.27; on a feature with a shared first part `lean` took 23.4 min and $4.53, regular 15 min
and $3.76. Quality was level or a little better with `lean` on both.

The router only SUGGESTS. If the user gave a mode, keep it and say what the router would pick.

### A2. Machine gate before any model check

A checker costs tokens. Do not spend it on work that does not build.

1. Every brief names the **gate commands** and the expected result (for example `npx tsc --noEmit`
   = exit 0; `npx vitest run <files>` = all pass).
2. After the builder ends, the SESSION runs the gate commands itself (never trust the builder's
   paste). Save the output to a file.
3. Gate red: the work goes back to the builder with the red output. This is NOT one of the 3
   adversarial rounds; maximum 2 gate returns, then report it.
4. Gate green: dispatch the checker, and give it the saved gate output.

Two sizes of gate (words used in Part B):

- **sub-task gate** = the type check + ONLY the test files of that sub-task + lint on the files it
  changed. It runs after each sub-task.
- **full gate** = type check + the FULL test suite + lint on all changed files. It runs three times
  at most: on the untouched base (save the red list, B6), before the check, and after the last fix
  round. Not after each sub-task.

The session saves the complete gate output to a file and reads ONLY: the exit codes, the summary
lines and the failed lines (`grep -E "exit|Test Files|Tests |FAIL| × |error" <file> | head -40`).
Never `cat` a full suite output into the session. A red line that is also red on the base is
written in the brief slot "Known red on the base" and does not count against the builder.

### A3. Standard checker brief

Use `multi-model-fix/templates/checker-brief-standard.md`. Rules it carries:

- The **diff is in the prompt**. The checker does not have to find it.
- The **gate output is in the prompt**. The checker does not run commands.
- Tools: **read and grep only. No shell. No web.** (A read-only Devin run that asks for a refused
  tool ENDS with no answer.)
- A **maximum number of tool calls** (default 15), then it must write the answer.
- A fixed answer form: `VERDICT: APPROVE | APPROVE WITH REQUIRED CHANGES | REJECT`, then findings
  as `file:line, severity, what, why`.
- What counts as medium / high for THIS job (or each round finds a new one-second race).

A checker that must run the tests itself (a break-restore proof) gets `--write` in its own worktree
and the old cross-check brief. Say which form you used.

### A4. No change without a check

Every pass that changes code after a check gets its own check: a fix for a "required change", a
type-only clean-up, a merge fix. The check may be small (the delta diff only, standard brief, max 8
tool calls), but it is never skipped. A pass with no second check is reported as UNCHECKED, by name.

### A5. Tokens, cost and time for every run

1. Pick one tag for the whole skill run: `<skill>-<YYYYMMDD>-<slug>`.
2. Devin runs: `DEVIN_RUN_TAG=<tag>-<step> $RUNNERS_DIR/devin/devin-run.sh ...` (step = `scout`,
   `b1`, `check1`, ...). The runner logs tokens, cached tokens, seconds and estimated cost to
   `$RUNNERS_DIR/devin/usage.jsonl`. Sum: `$RUNNERS_DIR/devin/devin-usage.py --tag <tag>`.
3. Other runners: copy the token line each one prints (Codex prints `tokens used`). If a runner
   prints none, write `n/a`, never a guess.
4. The session model's own tokens:
   `$RUNNERS_DIR/scripts/claude-usage.py --session <id> --since <ISO time> [--until <ISO time>]`
   (input, cache write, cache read, output, estimated cost; subagents included).
5. The report gets a third table:

   | step | model | time | input | cached | output | est. cost |

   with a total row. Costs are estimates from list prices; say so.

### A6. Keep the prompt cache warm

A subagent that waits for a run starts it in the background and waits in steps of 230 seconds at
most: `sliced-review/references/keep-warm.md`. This holds in every mode (`2`, `3`, `5`, `fast`,
`lean`) for every subagent that leads, builds or reviews, and it goes in the brief of each one.

---

## Part B — the `lean` mode

`/multi-fix lean`, `/multi-build lean`. Roles (defaults, the user 2026-10-07):

| role | default | why |
|---|---|---|
| lead | the session model (Opus) | plans, writes briefs, runs the gate, commits |
| scout | Devin SWE (`devin-run.sh --swe2`, read-only) | cheap reader |
| helper | Devin SWE (`devin-run.sh --swe2 --write`) | does the edits |
| checker | DeepSeek Flash (`devin-run.sh --deepseek`, read-only) | different model from the helper |

The no-self-check rule stays: the checker is never the helper's model. SWE costs money after
2026-10-15 ($3 / $0.30 / $15 per 1M): then ask the user which helper to use.

### B1. Scout first

Before the lead reads any code, one read-only scout run answers the lead's questions. Brief:
`multi-model-fix/templates/scout-brief.md`. The scout returns a **map**, not opinions:

- per item: the files and line ranges that matter, the function names, who calls them;
- the existing tests for that code and the exact command that runs them;
- the project's gate commands (type check, test, lint) and the conventions file, if there is one;
- anything it could not find, as `NOT FOUND`.

The lead then reads ONLY the line ranges on the map. The lead still verifies each item (multi-fix
Step 2, multi-build Step 2): the map says where to look, it does not say the item is real. A scout
fact the lead did not open is marked `scout says` in the ledger.

### B2. Short briefs only

Each sub-task brief:

- names **at most 2 production files to edit or create** (plus their test files) **with line
  ranges**. A NEW file counts as one of the 2. Test files do not count;
- is one change with one sub-task gate (A2);
- fits in about 10 minutes. A wider task is split before dispatch;
- points to the **item file** and does not repeat it.

**Item file (write each list ONE time).** Per item the lead writes one file,
`<briefs dir>/item-<id>.md`, from `multi-model-fix/templates/item-file.md`: the claim or wish
verbatim, the "done" lines (D1, D2 ...), the test list (T1, T2 ..., B5b), "must not break", and the
scout's map lines. The sub-task brief, the repro brief and the check brief all USE this file: the
helper reads it by its absolute path, and the check brief gets it by `cat` (B4). The lead never
types a done line or a test line a second time.

(Swift app 2026-10-07: 2 files + line ranges ended in 10 minutes; wide briefs took hours.)
Template: `multi-model-fix/templates/lean-brief.md`.

### B3. Groups of sub-tasks, each on autopilot (third pass 2026-10-08)

The first two tests showed: the lean lane lost its time to ONE helper in sequence and to the lead
standing between every two sub-tasks. So:

- **Group the sub-tasks by the files they edit.** Sub-tasks that edit a common file, or that need
  what another one writes, are one group, in order. A group = one worktree, one helper
  conversation, in sequence.
- **Groups that edit no file in common run at the same time**, 3 groups at most. (Two SWE runs
  at once use the free limit faster; the total work is the same.)
- **A seam first.** A file that several groups need (a shared helper, a type) is its own first
  group, alone. When it is gate green the lead commits it on the lean branch
  (`git -C <seam worktree> add -A && git commit -m "seam"`), and makes the other worktrees from
  that commit. Helpers never commit; the final commit in the project is still ONE (Step 8).
- **Autopilot.** Per group, one call:
  `multi-model-fix/templates/lean/lean-group.sh <group> <worktree> <briefs dir> <logs dir> <step>...`
  For each step it runs the helper with `<step>.md`, then the sub-task gate `gate-<step>.sh`
  (a few command lines the lead wrote from `lean/gate-example.sh`; exit 0 = green; lint counts
  NEW errors only), then the next step. A red gate goes back
  to the helper ONE time by itself, with the failed lines. It waits out a rate limit by itself.
  It stops and writes `RED <step>` when the gate stays red, or when the helper ends with
  `STOPPED` or `NOT REPRODUCED` (the lead decides: B5a). The helper keeps its conversation inside
  a group, and starts a fresh one when the last run had a request above 80k tokens.
- **The lead waits for ALL groups in one call**: `lean-wait.sh <logs dir> "<group> <group>"`
  (230 s at most per call, A6). When a group is done it prints the end of each helper log and the
  gate lines. The lead READS these: every `NOT TESTED` line and every changed file outside the
  brief is the lead's to judge. The machine gate rule (A2) holds: the gate ran outside the helper.
- A single Devin run that is not a group (scout, checker): `lean-run.sh`, then `lean-wait.sh`.
- Never `--continue` in a directory another run used: it takes that run's conversation.
- Every brief is complete by itself (item file path + lines), because the helper may start fresh.

### B4. One tree, one full gate, one check on the whole diff

When all groups are GREEN:

1. `lean-collect.sh <integration dir> <out.patch> <group worktree>...` brings every group's
   changes into ONE tree (a detached worktree at the BASE commit, with the dependencies in place)
   and writes the complete diff against the base; a seam commit is applied one time. It fails if
   two groups edited the same file. This patch is what the checker gets and what Step 8 commits.
2. The full gate (A2) runs in the integration tree.
3. ONE checker run on the complete diff with the standard brief (A3), in the integration tree.
   NEVER in a helper's worktree: a run there becomes the conversation that the helper's next
   `--continue` takes. Items closed without a change go in the same brief (B5a).
4. Required changes: a short brief to the group that owns the file
   (`lean-group.sh <group> <its worktree> ... fix1`), then `lean-collect.sh` again: it writes
   `<out.patch>.delta` = only what changed. The delta check (A4) gets that diff. The full gate
   runs again one time, after the last round. Maximum 3 rounds, as in the other modes.

- **Build the check brief with the shell, do not type it.** `lean-mkcheck.sh` joins: a short head
  the lead writes (repo path, what counts as high / medium), the item files, the
  closed-without-change block, the trimmed gate output, the diff, and the fixed "Do this" + answer
  form. `-p "<one line>"` adds the `PART k of n` line or the delta-check line. The lead does not
  read the built file back.
- **Split check.** Above about 600 changed lines, split the diff by area into 2 or more checker
  runs at the same time (two read-only runs may share the integration tree). Each brief says
  `PART k of n`, names its items, and says the other parts are out of scope. Result = the worst
  verdict of the parts; the report lists each part.
- **Severity is the lead's call.** The checker's `low` on a missing refusal test, a missing
  side-effect assertion or a missing named edge input is `medium` by B5c: the lead sends it back.

### B5. Quality rules (added 2026-10-08, after three A/B tests)

The tests showed where `lean` lost points: one real defect closed as "not real" by the lead alone
(1 of 10 points on that item), and thinner tests than the parallel modes. Three rules repair this.

**B5a. No item is closed without a change unless a test and the checker agree.**
The lead must NOT close an item as "not real", "already fixed" or "cannot happen" from reading the
code. Before that:

1. The helper gets `multi-model-fix/templates/repro-brief.md` (with `--continue`): write a test
   that tries to SHOW the defect, in the exact sequence the item describes (for a race: the
   interleaving the item names, forced with the project's test tools). Run it. Paste the output.
2. The test shows the defect: the item is real. The helper fixes it in the SAME run when the
   repro brief has the "Then, in the same run" part filled in (use it when the item file has the
   done lines and the test list); else send the normal fix brief.
3. The test cannot show it: the item goes to the checker as `CLOSED WITHOUT CHANGE`, with the
   lead's reason and the repro test in the check brief. The checker answers `closed ok` or
   `still real` for it. `still real` = fix it (this counts as a required change).
4. An item closed with no repro test, or with no checker answer, is reported as
   `CLOSED UNCHECKED`, by name, in the summary line of the report. Never as "fixed" or "done".

**B5b. Every brief carries a test list.**
The lead writes, per sub-task, the cases the tests must cover, from the item's "done" lines:

- each refusal / error path the item names, one case each, with the exact message or value;
- each success path, with the value that must come back and the side effects that must happen;
- for a failure path: the side effects that must NOT happen (no audit row, no redirect, no write);
- the edge inputs the item names (empty, array, null, over the limit).

The helper writes one test per line of the list. A line it cannot test is returned as
`NOT TESTED <line> + reason`, never dropped in silence. The gate for the sub-task includes those
test files. The list lives in the item file (B2), one time.

Two items need no new test, and the test list says so in one line:

- `NONE: type-only change`: the gate is the type check + the existing tests of the file.
- `TEST-ONLY: the tests are the change`: each test must go red under the named break
  (`break: <what to change in the code> -> <test> fails`), then green after the restore.

**B5c. The checker gets the "done" list and the test list.**
The check brief (A3) carries, per item, the "done" lines from the spec / ledger and the B5b test
list, not only the required behaviour in one sentence. The checker answers per "done" line
(`met | partly | not met`) and per test-list line (`covered by <test name> | missing`). A missing
line on a refusal, a side effect or a named edge input is `medium` = a required change.

Cost: one extra helper turn per doubtful item (none when the repro and the fix share a run) and a
longer check brief (built by the shell, B4). Measure it in the A5 table.

### B6. Traps the test runs found

- Never wait for a helper with `pgrep -f <text>`: the pattern matches the waiting shell itself and
  the loop never ends. Run the runner in the foreground, or wait on its PID.
- Never run `devin-run.sh --help`: it starts a real, untagged model run.
- Measure the base first: run the full gate on the untouched base commit and save the red list.
  A test that is red on the base is not the helper's failure.
- Never replace `devin-run.sh` while a run is active.

### B7. What `lean` gives up

One builder model's eyes only (the groups are the same model). Say so in the report. If the checker rejects two
times, or the job grows past the A1 table, stop and offer `3`.
