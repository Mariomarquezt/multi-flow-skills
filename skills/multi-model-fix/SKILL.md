---
name: multi-model-fix
version: 2.5.0
description: Fix a list of defects with several models at once — from ANY source, not just a sliced review — the way sliced-review's fix modes do it: verify each defect against the code, split the work by FILE ownership and spread it evenly across the models, brief each fixer to observe the failure before and after, have a DIFFERENT model cross-check every fix, run the full suite on the settled tree, then one commit. Input can be pasted text, a bug report, a Sentry or GitHub issue, a PR review, a failing test, a review file from any tool, or docs/reviews/findings.json. Use when the user says "fix these with multiple models", "multi-model fix", "have the models fix this", "fix the findings from <anything>", "split these fixes across the models", or invokes /multi-fix or /multi-model-fix (same skill). MODES: `2` = one defect, two models — Sol fixes, Grok checks; bare or `3` = core three fixers (Sol high via Codex, Grok via Cursor, Opus subagent) taking even shares with rotated cross-check; `5` = the main roster (core three + DeepSeek Flash + GLM Flash); `fast` = Composer fixes and Sol checks; `lean` = SWE helpers with short briefs after a scout, groups in parallel on autopilot, DeepSeek Flash checks (best for separate defects; a feature with a shared first part = `3`); `high` = critical and high only; `dry` = verify and plan the split, edit nothing; append `report` for a Markdown + HTML fix report, `no wrap` to skip the closing /wrap lite. NOT for finding defects (use /sliced-review or /multi-model-review), NOT for a single one-line fix the session can do itself, and NOT a substitute for the user's approval on data deletion, migrations, public interfaces, credentials or billing.
---

# Multi-model fix

> **Model names are short names** (Sol, Grok, Opus, GLM Flash, Composer, DeepSeek Flash, …). The exact version of each lives in ONE place: `~/.claude/skills/_shared/models.md`. Read it before the first dispatch, and write the exact model id from it in every report. Never pick a model by "latest".
>
> **Grok here = the `Grok (fix, build)` row of models.md (Grok 4.7).** Reviews use Grok 4.6; this skill stays on 4.7 until the user moves it (2026-10-25).
>
> **Gemini (Antigravity, added 2026-11-17):** Gemini Hydrogen / Carbon / Argon / Flash are in models.md as extra
> lanes — no mode uses them until the user moves them in. Swap one in only when the user asks. Runner:
> `$RUNNERS_DIR/antigravity/agy-run.sh` (`--write` for a fixer). One Gemini lane never checks another Gemini
> lane's work; Gemini Flash on Antigravity and on Cursor is one model.

Take defects from anywhere. Fix them with several models. Nobody checks their own work. One commit.

This is the fix half of `sliced-review` (its fix modes hand off here, Step 11c), so it runs on **any** input in
**any** session. `sliced-review fix only` is this procedure with `findings.json` as the input; if
that file exists and is what the user means, prefer `/sliced-review fix only` so the review's
records stay in one place. Everything else — a pasted list, a bug report, a Sentry issue, a PR
review, a failing test — comes here.

## The one idea

A fix nobody else looked at is a hypothesis with a green test. The model that wrote a fix shares the
reasoning that produced the bug, so it cannot see the second unsigned path it left open or the test
it wrote that asserts the wrong name. Measured, repeatedly (sliced-review `FIELD-NOTES.md`,
multi-model-review Phase 4). So: **every fix is written by one model and checked by a different one,
and the models take equal shares of the writing.** The second rule is the user's (2026-08-23): a "clean
triangle" where one model fixes everything and the others only review is not what they want.

## Router suggestion — run before assigning models (suggest mode, 2026-10-03)

Before you split the work, ask the model router which arms have quota to spare:

```sh
$RUNNERS_DIR/router/router suggest --task "<one-paragraph job summary>" --files <N> --items <N> --mode fix --n <builders>
```

`--n` = the number of builders the mode uses (`2` -> 1, `3` -> 3, `5` -> 5, `fast` -> 1). It prints
quota-aware builder/checker pairs, the job difficulty (rules, plus Laya and Jev in shadow) and a
decision id. **Suggest mode:** state the router's pick next to the mode's default pick in your
one-line mode statement. Keep the default ring unless the user agrees to the router's pick, or a
default arm's plan is BLOCKED/near empty (then take the router's substitute and say so). The
no-self-check and different-subscription rules still win over the router.

After the cross-check settles, log one outcome per arm that built or checked (this is the
training data — do not skip it):

```sh
$RUNNERS_DIR/router/router outcome --id <decision id> --arm <arm> --role builder|reviewer --result pass|fail|redo [--actual easy|medium|hard] [--found <defects the check found>]
```

Arm names, rules and the $3 Jev cap: `$RUNNERS_DIR/router/README.md`. If the router errors or
Codexbar hangs, carry on with the default ring and note it in the report.

## Modes — parse the invocation FIRST, state it back in one line

`/multi-fix` and `/multi-model-fix` are the same skill. The number is how many models take part.

| invocation | fixers | cross-check | scope |
|---|---|---|---|
| `/multi-fix 2` | **one**: Sol (Codex, high) | **one**: Grok (Cursor, high) | one defect, or a small handful — one bundle, one fixer, one checker |
| `/multi-fix` or `/multi-fix 3` | **core three**: Sol (Codex, high), Grok (Cursor, high), Opus (subagent, high) — each takes an even share | rotated A→B→C→A | all verified defects |
| `/multi-fix 5` | the main roster: core three + DeepSeek Flash + GLM Flash (providers picked) — even share across five | fixed ring: Sol → GLM Flash → Opus → DeepSeek Flash → Grok → Sol | all |
| `/multi-fix fast` | Composer only | Sol (Codex, high) | all — cheap sweep, say so |
| `/multi-fix lean` | **one helper**: Devin SWE, short briefs in sequence, after a SWE scout | **one**: DeepSeek Flash (Devin), on the whole diff | 1 to 6 defects in 8 files or fewer. Not for security, money, migrations or auth. See "Lean lane" |
| `/multi-fix high` | as the number says (default three) | rotated | **critical + high only** |
| `/multi-fix dry` | nobody edits | — | verify + write the split; stop |
| `… report` (suffix) | — | — | also build the Markdown + HTML fix report (Step 9) |
| `… no wrap` (suffix) | — | — | skip the closing `/wrap lite` |

Compose freely: `2 report`, `5 high`, `fast report`, `3 high dry`, `5 report no wrap`.

**`2` is the small-job mode.** One model fixes, a different one checks — the minimum that still
honours the no-self-review rule. Use it for one defect or a few that share a file. It does not
split work, so the even-share rule does not apply; if the ledger has more than one bundle, say so
and suggest `3`. Default pair is Sol fixing and Grok checking; the user may name another pair, but
never Opus checked by Claude, and never Sol or Opus via Cursor.

**`3` is the default** and the explicit alias for bare `/multi-fix`, so the model count can be said
out loud. `5` spreads the same work thinner and adds two independent checkers.

**A fix and its check are never on the same subscription.** Grok and Composer both bill to Cursor,
so they never check each other; that is why `fast` pairs Composer with Sol. DeepSeek Flash and GLM
Flash can land on the same provider, so they are never adjacent: the five-ring is fixed as
Sol → GLM Flash → Opus → DeepSeek Flash → Grok → Sol (each fix is checked by the next), and Opus is checked by DeepSeek Flash, never by Claude.

**Providers come from `~/.claude/skills/_shared/models.md`.** Opus = a subagent on the user's own Claude
session. Sol and Luna = Codex. Composer = Cursor. Grok, DeepSeek Flash, GLM Flash, Qwen Flash and
MiMo Flash have several providers: run `~/.claude/skills/sliced-review/references/pick-provider.py
--model "<name>"` and use the subscription whose tokens expire first. Wiring and traps:
`~/.claude/skills/sliced-review/references/runners.md`. Never route Sol or Opus through Cursor.

**Provider notes: read `~/.claude/skills/sliced-review/references/runners.md` → "Provider notes" before the first dispatch.** It holds the
Swift rule (Sol builds Swift through OpenCode, not Codex), Luna, Pi as the main OpenCode driver,
the free OpenCode and Cline arms, xAI and Devin, and which routes run the SAME model — two routes
of one model are never a fix and its cross-check, nor two reviewers in one scorecard.

**Opus is Claude.** A fix Opus wrote is cross-checked by Sol or Grok, never by another Claude
subagent and never by the session model. The session model's approval in Step 8 is an integration
gate, not an independent review — say so.

## Lean lane and run rules (added 2026-10-08) — read `~/.claude/skills/sliced-review/references/lean-lane.md`

That file is part of this skill. Read it before Step 1. In short:

**Run rules, EVERY mode:**

- **Size router (A1).** After Step 3, count the queued rows and files. 1 to 6 rows in 8 files or
  fewer, nothing about security, money, migrations or auth: suggest `lean`. Else `3` or `5`. Short form:
  **separate defects = `lean`; a feature with a shared first part = regular (`3` or `5`).** The
  user's mode wins; say what the router would pick.
- **Machine gate (A2).** Each brief names the gate commands and the expected result. The SESSION
  runs them after the fixer ends. Red goes back to the fixer (max 2 returns, not counted as a
  round). The checker starts only on green, and gets the gate output.
- **Standard checker brief (A3).** `templates/checker-brief-standard.md`: diff and gate output in
  the prompt, read and grep tools only, a maximum number of tool calls, a fixed answer form. A
  checker that must run the break-restore itself keeps `templates/cross-check-brief.md` and a
  writable worktree.
- **No change without a check (A4).** Each pass that changes code after a check gets its own check
  on the delta diff. A pass with no check is reported as UNCHECKED.
- **Tokens, cost, time (A5).** One tag per skill run (`DEVIN_RUN_TAG=<tag>-<step>`), the session's
  own tokens from `$RUNNERS_DIR/scripts/claude-usage.py`, and a third report table (Step 9).

**`lean` mode (Part B):** lead = session model; scout = SWE read-only
(`templates/scout-brief.md`) BEFORE the lead reads code, the lead then opens only the line ranges on
the map and still verifies each row (Step 2); briefs = `templates/lean-brief.md`, at most 2 production files (a new file counts) +
line ranges, one change, one sub-task gate; ONE helper MODEL (SWE); sub-tasks in groups, a worktree per group, gate after each
(see "Third pass" below); ONE DeepSeek Flash
check on the whole diff. Steps 3 to 5 and 7 below shrink to that; Steps 1, 2, 6, 8, 9, 10 and the
honesty rules stay. The even-share rule does not apply (one helper, by choice of the mode). Checker
is never the helper's model.

**Quality rules for `lean` (B5, added after the 2026-10-08 A/B tests):** (a) the lead never closes
a row as "not real" from reading alone: the helper first gets `templates/repro-brief.md`, and a row
with no change goes to the checker as `CLOSED WITHOUT CHANGE` (else report `CLOSED UNCHECKED`);
(b) every brief carries a test list (each refusal, each success with its side effects, failure side
effects that must not run, named edge inputs), one test per line; (c) the check brief carries the
"done" lines and the test list, and the checker answers per line.

**Cost and time rules for `lean` (second pass 2026-10-08, lean-lane.md A2, B2, B3, B4):** (1) one
ITEM FILE per item (`templates/item-file.md`): claim, done lines, test list, map, written ONE time; briefs
point to it, the check brief gets it by `cat`; (2) the lead reads only exit codes, summary lines
and failed lines of a gate output; (3) a fresh helper conversation when the area changes or after 5
sub-tasks; (4) sub-task gate (type check + that sub-task's tests + lint on its files) after each
sub-task, the full suite only on the base, before the check and after the last round; (5) a repro
test and its fix in ONE helper run; (6) start every Devin run with `templates/lean/lean-run.sh`, wait with
`templates/lean/lean-wait.sh` (230 s at most per wait: a 5-minute prompt cache must not run out), build the
check brief with `templates/lean/lean-mkcheck.sh`; (7) the checker never runs in the helper's worktree.
When the work runs on another machine, copy the scripts there first.

**Third pass (2026-10-08, lean-lane.md B3, B4):** sub-tasks are put in GROUPS by the files they
edit; groups with no common file run at the same time (3 at most), each in its own worktree, on
autopilot with `templates/lean/lean-group.sh` (helper, sub-task gate `gate-<step>.sh`, one automatic gate
return, next step); a seam file is its own first group; the lead waits for all groups in one
`lean-wait.sh` call and reads the summaries; `templates/lean/lean-collect.sh` joins the groups into one
integration tree for the full gate and the check, and writes the delta after a fix round.


Create a todo per step and work them in order.

## Step 1 — Intake: turn whatever arrived into a fix ledger

Input arrives in every shape. Normalise it before anything else into
**`docs/fixes/<YYYY-MM-DD>-<slug>.md`** (create `docs/fixes/`), one row per defect:

| id | title | file:line | severity | source | evidence | constraint |
|---|---|---|---|---|---|---|

- `id`: `fx-01` … in the order received.
- `file:line`: **a real path in this tree**, resolved now. If the source names no file, find it
  (grep the symptom, read the stack trace, open the failing test) and record how. A defect with no
  file is not fixable; it goes in the ledger with `file: UNRESOLVED` and is reported, not dispatched.
- `severity`: **yours**, at triage — critical / high / medium / low — never the source's label
  copied through. A Sentry "error" and a reviewer's "critical" are both claims.
- `source`: where it came from (`pasted`, `sentry:<id>`, `gh:#123`, `pr-review`, `test:<name>`,
  `file:<path>`).
- `evidence`: what you read that says it is real, or "unverified — see Step 2".
- `constraint`: what the fix must not break — the public contract, the data, the behaviour a test
  pins.

Accepted inputs, and what to do with each:

- **Pasted text / a message** — one row per distinct defect; merge duplicates.
- **A file** (`.md`, `.txt`, `.json`, a review report) — parse it; keep its ids in `source`.
- **`docs/reviews/findings.json`** — stop and offer `/sliced-review fix only` instead. If the user
  insists on this skill, rows = the `open` entries; keep their ids.
- **Sentry / GitHub issue / PR review** — pull it with the tool you have (Sentry MCP, `gh`), quote
  the exact error text, resolve the file from the trace.
- **A failing test** — run it once, capture the output, the file is the code under test.

If the ledger ends up with one row and a one-line fix, say so and offer to just fix it. This skill
is overhead for a typo.

## Step 2 — Verify every row against the CURRENT tree. Disprove first.

Per sliced-review Step 10: a defect report is a hypothesis, not a fact — it will confidently
describe a missing check that exists two frames up. For each row, read the code at `file:line` and
its neighbourhood, and prefer an experiment to an argument: run the failing case, build the artifact
and grep it.

Outcomes, all written into the ledger's `evidence` column before any fixer is briefed:

- **Confirmed** — say what you saw. Enters the queue.
- **Already fixed** — by which commit (`git log -S'<symptom>'`). Recorded, not queued.
- **Refuted** — say which claim you refuted **and which you did not test**. "Not in the artifact"
  and "not publishable" are different claims. A refuted claim is not a closed concern: if the
  worry survives the refutation, keep the row as `open — concern only` and tell the user.
- **Cannot tell** — the evidence needs a database, a running service, a credential you lack. Goes
  to the user with the exact question; not queued.

In `high` mode, rows below HIGH stay in the ledger as `open` and are **not** queued. Never delete a
row.

**Report the ledger to the user before any edit.** They decide what gets fixed. In `dry` mode this
is where the work ends, after Step 3's split is written.

## Step 3 — Map write sets, split by FILE, split EVENLY across models

Two agents editing one file concurrently clobber each other, and one of them reports success. So:

1. For every queued row, list the files the fix will touch — read enough to know, do not guess.
2. **Bundle rows that share a file under one owner.** An unavoidable overlap is serialised, never
   parallelised.
3. **Distribute the bundles as evenly as the file boundaries allow** — twelve fixes across three
   models is four each, not twelve to one. If the bundles cannot be made even (one file holds nine
   of the twelve), say so and ask the user how to split, or run it in two waves. Never default to
   one model fixing everything.
4. Assign each bundle's **cross-checker** now, before fixing: the next model around the ring, never
   the author, never Claude-for-Opus. With `fast`, Sol checks everything Composer wrote — a cheap fixer gets the strongest checker,
   and the two are on different subscriptions, so neither bill hides the other.
5. Write the split into the ledger as a second table: bundle → files → fixer → checker.

Disjoint files are necessary, not sufficient — an interface change in one file breaks a caller in
another. That is what Step 7 is for.

## Step 4 — Brief and dispatch the fixers, one worktree each

Use `templates/fix-brief.md`. Every brief carries, per row: the file and line, **why you believe it
is real from having read the code** (Step 2's evidence, not the source's words), the constraint,
and a suggested mechanism the fixer may reject. Also:

- The **exact files it may modify**, that other agents are working in the same repo right now, and
  an explicit list of files it must **not** touch. If the footprint grows beyond the declared files
  it stops and asks — it does not reach into another owner's file.
- **No `git commit` / `add` / `checkout` / `stash`.** Leave everything in the working tree. A
  pre-commit hook that rebuilds a release artifact will happily rebuild at a published version.
- **Observe the failure.** Before the fix, run the failing case and paste the output. After the fix,
  deliberately break it, watch the test or gate fail *for the defect's reason*, restore, paste both.
  A syntax error that turns the suite red proves nothing. A fix nobody watched fail is UNVERIFIED
  and the brief says to label it so.
- **Where the break happens.** Give each fixer its own `git worktree` on its own branch
  (`git worktree add ../<project>-fx-<model> -b fx/<date>-<model>`) so one agent's break-restore
  does not fail another agent's suite. If a worktree is impossible, the break-restore runs in a
  copy of the tree, or the fix is marked UNVERIFIED.
- Cases a naive fix will not cover, when you already know them. Fix **the test too** when it passes
  only because it manufactures its own precondition.
- **Refusing a row with an explanation is a valid, welcome outcome.** Record it in the ledger.

Dispatch all fixers in parallel. Every run has a hard wall-clock cap (30 min default) and the
watchdog rules from sliced-review Step 6 — a hung backend must not look like a slow one.

Before dispatching, read `~/.claude/skills/sliced-review/references/runners.md` →
**"Orchestration gotchas"** (never launch a long job with `nohup … &` inside a tool shell — it
detaches, gives no completion notification, and can be killed with the shell; use tracked
background instead; work in a dedicated read-only worktree at the right commit; write into the
synced tree) and **"Gotchas that keep biting — per backend"** + **"Linux laptop"**. These encode
errors we have already made; don't repeat them.

## Step 5 — Cross-check every fix with a model that did not write it

Use `templates/cross-check-brief.md`. Give the checker **the claim, not just the diff**: here is the
change, here is what the fixer claims it proves, here is the before/break/after output it pasted.
Name any file another fixer is still editing and tell the checker to skip it — a review of a
half-written file is noise.

The checker returns one of: **approve**, **approve with a required change** (specific, file and
line), **reject** (with the case the fix misses, demonstrated if possible). A "looks good" without
having run anything is not an approval; send it back.

## Step 6 — When it is still not right: adversarial rounds, MAXIMUM THREE

Fixer answers the checker; checker re-checks. Three rounds, then stop. If they still disagree the
defect goes to the user **with the disagreement stated**, not resolved by whoever spoke last, and the
rest of the queue keeps moving.

## Step 7 — The settled-tree pass

Merge every fixer's worktree into one integration branch. Run the **full suite on the whole tree** —
per-bundle checks miss cross-file integration defects, and no single fixer is eligible to review the
combined result. Give the complete diff to whichever model authored the **least** of it; if every
model authored a lot, to a fourth model or the user. Any file skipped during Step 5 for being
mid-edit is reviewed **here**. Nothing is finished while that queue is non-empty.

If the settled-tree pass fails, nothing is committed. Report it.

## Step 8 — The session model approves and commits. Once.

Read the whole diff yourself. This is the integration gate and the human-facing decision — **not a
third review**, and never call it one. Then **one commit** (no per-fixer commits), message listing
the ledger ids, then remove the worktrees.

**What still stops the pipeline, in every mode.** A fix that would delete or migrate data, change a
public interface, touch credentials or billing, or where the models disagree about whether the
defect is real. Those go to the user with the question stated. The user's invocation authorised
fixing what Step 2 confirmed — not acting on anything.

## Step 9 — Record, and the report

1. **The ledger** gets its final columns: fixer, checker, verdict, `verified` (yes only if the
   break-restore was seen), `commit`. This file is the record of the run.
2. **If the project has `docs/reviews/findings.json`**, add a review record
   `{ id: "fix-<date>", model: "multi-model-fix", kind: "ad-hoc", dir: "docs/fixes", slices: 0 }`
   and one entry per ledger row that was confirmed, with `status: fixed`, `fixed_at`,
   `fix_commit` — or `open` / `false-positive` / `wontfix` with a note. Refuted rows go in as
   `false-positive`. Never delete. Then the board and Mission Control see this work too.
3. **If the project has a user-facing changelog**, one row per defect fixed, written for the
   reader, not the engineer.
4. **Report to the user** — two tables, always:

   | id | title | severity | fixer | checker | rounds | verified | result |

   | model | fixes assigned | approved first pass | rejected / refused | time |

   | step | model | time | input | cached | output | est. cost |

   (one row per run: scout, each fixer, each check, the session model; then a total row; lean-lane.md A5.)

   Then the stops: anything that went to the user unfixed, and why. Name every UNCHECKED pass.
5. **`report` suffix, or ask once** — "Build the Markdown + HTML fix report? (y/n)". If yes, run
   `python3 ~/.claude/skills/sliced-review/templates/build-report.py --project <root>` when
   `findings.json` exists (it renders the ad-hoc record with the rest); otherwise render the ledger
   to `docs/fixes/<date>-<slug>.html` with the same page style. Never build it unasked.

## Step 10 — `/wrap lite`, unless `no wrap`

## Honesty rules

- Never dispatch a row you did not verify against the current tree. The source's confidence is not
  evidence.
- Never report a fix as verified when nobody watched it fail for the defect's reason.
- Never let a model check its own fix, and "own" means the model family — Opus is Claude.
- Never present the session model's approval as an independent review.
- Never give all the fixes to one model without asking. Even split, or the user chooses.
- Never report a consensus the adversarial rounds did not reach. State the disagreement.
- Never commit per fixer. The tree is only known good after Step 7.
- Never send a checker work that the machine gate did not pass.
- Never close a row / part with no change unless a repro test AND the checker agree; else report it as CLOSED UNCHECKED.
- Never leave a later pass (required change, clean-up, merge fix) without its own check, or report it as UNCHECKED.
- Never report a token or cost figure you did not read from a log. `n/a` is a valid cell.
- Never delete a ledger row. Refused, refuted and skipped rows stay, with the reason.

## Keep the prompt cache warm (added 2026-10-08)

A Claude subagent loses its prompt cache after 5 minutes without a request, and then pays for its
whole context again (about $0.75 each time). So: no tool call of a subagent waits longer than 230
seconds. Start every long run (builder, reviewer, `codex exec`, a long test suite) in the
background and wait in short steps, with the scripts and the rule in
`~/.claude/skills/sliced-review/references/keep-warm.md`. Put this rule in the brief of every
subagent that will wait for a run.
