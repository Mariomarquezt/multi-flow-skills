---
name: multi-build
version: 2.5.0
description: Build ONE new feature with several models at once, the way multi-fix fixes defects — write a spec with testable acceptance criteria first, agree the interfaces between the parts before anyone codes, split the work by FILE ownership evenly across the models, brief each builder to write the failing test first, have a DIFFERENT model on a DIFFERENT subscription review every part against the spec, integrate, run the full suite, one commit. Use when the user says "build this with multiple models", "multi-build", "have the models build this feature", "split this feature across the models", or invokes /multi-build. MODES: `2` = one model builds (Sol), one reviews (Grok) — a small feature in one or two files; bare or `3` = core three builders (Sol high via Codex, Grok via Cursor, Opus subagent) taking even shares with rotated review; `5` = the main roster (core three + DeepSeek Flash + GLM Flash) on a fixed ring; `fast` = Composer builds, Sol reviews; `lean` = SWE helpers with short briefs after a scout, groups in parallel on autopilot, DeepSeek Flash reviews (small features with separate parts; a feature with a shared first part = `3`); `dry` = spec + interfaces + split, no code; append `report` for a Markdown + HTML build report, `no wrap` to skip the closing /wrap lite. NOT for fixing defects (use /multi-fix), NOT for a whole app from an interview (use /full-build), NOT for one model building from a frozen plan (use /codex-build), and NOT a substitute for the user's approval on data migrations, public interfaces, credentials or billing.
---

# Multi-build

> **Model names are short names** (Sol, Grok, Opus, GLM Flash, Composer, DeepSeek Flash, …). The exact version of each lives in ONE place: `~/.claude/skills/_shared/models.md`. Read it before the first dispatch, and write the exact model id from it in every report. Never pick a model by "latest".
>
> **Grok here = the `Grok (fix, build)` row of models.md (Grok 4.7).** Reviews use Grok 4.6; this skill stays on 4.7 until the user moves it (2026-10-25).
>
> **Gemini (Antigravity, added 2026-11-17):** Gemini Hydrogen / Carbon / Argon / Flash are in models.md as extra
> lanes — no mode uses them until the user moves them in. Swap one in only when the user asks. Runner:
> `$RUNNERS_DIR/antigravity/agy-run.sh` (`--write` for a builder). One Gemini lane never checks another Gemini
> lane's work; Gemini Flash on Antigravity and on Cursor is one model.

One feature. Several models build it in parallel. Nobody reviews their own part. One commit.

This is `multi-fix`'s machinery — even split by file, one worktree per agent, a different model on a
different subscription checks every piece, settled-tree pass, one commit — with a different front
half. A defect arrives with a file and a line and is proven by watching it fail. A feature arrives as
a wish, and has to be turned into **testable acceptance criteria and agreed interfaces** before
three agents can build pieces of it at the same time without building three different things.

## The one idea

Parallel building fails in one specific way: each builder makes a private assumption about the
seam between its part and the next, and the assumptions disagree. The integration step then
discovers three correct components that do not fit. So the session model writes the **seams first**
— the function signatures, the types, the routes, the table shape, the event names — as a contract
every brief carries verbatim. Builders fill in behind a contract; they do not invent one.

Second idea, inherited: **the model that built a part cannot see what it did not build.** A
different model, on a different bill, reviews it against the spec — and looks for what the builder
did not test.

## Router suggestion — run before assigning models (suggest mode, 2026-10-03)

Before you split the work, ask the model router which arms have quota to spare:

```sh
$RUNNERS_DIR/router/router suggest --task "<one-paragraph job summary>" --files <N> --items <N> --mode build --n <builders>
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

The number is how many models take part.

| invocation | builders | review | scope |
|---|---|---|---|
| `/multi-build 2` | **one**: Sol (Codex, high) | **one**: Grok (Cursor, high) | a small feature — one bundle, one or two files |
| `/multi-build` or `/multi-build 3` | **core three**: Sol (Codex, high), Grok (Cursor, high), Opus (subagent, high) — even shares | rotated A→B→C→A | the normal case |
| `/multi-build 5` | the main roster: core three + DeepSeek Flash + GLM Flash (providers picked) — even shares | fixed ring Sol → GLM Flash → Opus → DeepSeek Flash → Grok → Sol | a large feature with many separable parts |
| `/multi-build fast` | Composer only | Sol (Codex, high) | cheap and quick — say so |
| `/multi-build lean` | **one helper**: Devin SWE, short briefs in sequence, after a SWE scout | **one**: DeepSeek Flash (Devin), on the whole diff | a small feature: 1 to 6 sub-tasks in 8 files or fewer. Not for security, money, migrations or auth. See "Lean lane" |
| `/multi-build dry` | nobody codes | — | spec, seams, split; stop and show the user |
| `… report` (suffix) | — | — | also build the Markdown + HTML build report (Step 9) |
| `… no wrap` (suffix) | — | — | skip the closing `/wrap lite` |

Compose freely: `2 report`, `5 dry`, `fast report no wrap`.

**A part and its review are never on the same subscription.** Grok and Composer both bill to Cursor
and never review each other; `fast` pairs Composer with Sol. DeepSeek Flash and GLM Flash can land on
the same provider, so the five-ring keeps them apart: Sol → GLM Flash → Opus → DeepSeek Flash → Grok → Sol, and Opus is reviewed by DeepSeek Flash,
never by Claude.

**Providers come from `~/.claude/skills/_shared/models.md`.** Opus = a subagent on the user's own Claude
session. Sol and Luna = Codex. Composer = Cursor. Grok, DeepSeek Flash, GLM Flash, Qwen Flash and
MiMo Flash have several providers: run `~/.claude/skills/sliced-review/references/pick-provider.py
--model "<name>"` and use the subscription whose tokens expire first. Wiring and traps:
`~/.claude/skills/sliced-review/references/runners.md`. Never route Sol or Opus through Cursor.

**Provider notes: read `~/.claude/skills/sliced-review/references/runners.md` → "Provider notes" before the first dispatch.** It holds the
Swift rule (Sol builds Swift through OpenCode, not Codex), Luna, Pi as the main OpenCode driver,
the free OpenCode and Cline arms, xAI and Devin, and which routes run the SAME model — two routes
of one model are never a fix and its cross-check, nor two reviewers in one scorecard.

**Opus is Claude.** The session model's approval in Step 8 is an integration gate, not an
independent review — say so.

## Lean lane and run rules (added 2026-10-08) — read `~/.claude/skills/sliced-review/references/lean-lane.md`

That file is part of this skill. Read it before Step 1. In short:

**Run rules, EVERY mode:**

- **Size router (A1).** After Step 3, count the parts and files. 1 to 6 sub-tasks in 8 files or
  fewer, nothing about security, money, migrations or auth: suggest `lean`. Else `3` or `5`. Short form:
  **separate defects = `lean`; a feature with a shared first part = regular (`3` or `5`).** The
  user's mode wins; say what the router would pick.
- **Machine gate (A2).** Each brief names the gate commands and the expected result. The SESSION
  runs them after the builder ends. Red goes back to the builder (max 2 returns, not counted as a
  round). The checker starts only on green, and gets the gate output.
- **Standard checker brief (A3).** Diff and gate output in
  the prompt, read and grep tools only, a maximum number of tool calls, a fixed answer form. Template: `~/.claude/skills/multi-model-fix/templates/checker-brief-standard.md`
  (add the spec and the seams above the diff). A reviewer that must run the tests itself keeps
  `templates/review-brief.md` and a writable worktree.
- **No change without a check (A4).** Each pass that changes code after a check gets its own check
  on the delta diff. A pass with no check is reported as UNCHECKED.
- **Tokens, cost, time (A5).** One tag per skill run (`DEVIN_RUN_TAG=<tag>-<step>`), the session's
  own tokens from `$RUNNERS_DIR/scripts/claude-usage.py`, and a third report table (Step 9).

**`lean` mode (Part B):** lead = session model; scout = SWE read-only
(`~/.claude/skills/multi-model-fix/templates/scout-brief.md`) BEFORE the lead reads code, the lead then opens only the line ranges on
the map and still writes the spec and the seams itself (Steps 1, 2); briefs =
`~/.claude/skills/multi-model-fix/templates/lean-brief.md` + the seams verbatim, at most 2 production files (a new file counts) +
line ranges, one change, one sub-task gate; ONE helper MODEL (SWE); sub-tasks in groups, a worktree per group, gate after each
(see "Third pass" below); ONE DeepSeek Flash
check on the whole diff. Steps 3 to 5 and 7 below shrink to that; Steps 1, 2, 6, 8, 9, 10 and the
honesty rules stay. The even-share rule does not apply (one helper, by choice of the mode). Checker
is never the helper's model.

**Quality rules for `lean` (B5, added after the 2026-10-08 A/B tests):** (a) the lead never closes
a row as "not real" from reading alone: the helper first gets `~/.claude/skills/multi-model-fix/templates/repro-brief.md`, and a row
with no change goes to the checker as `CLOSED WITHOUT CHANGE` (else report `CLOSED UNCHECKED`);
(b) every brief carries a test list (each refusal, each success with its side effects, failure side
effects that must not run, named edge inputs), one test per line; (c) the check brief carries the
"done" lines and the test list, and the checker answers per line.

**Cost and time rules for `lean` (second pass 2026-10-08, lean-lane.md A2, B2, B3, B4):** (1) one
ITEM FILE per item (`~/.claude/skills/multi-model-fix/templates/item-file.md`): claim, done lines, test list, map, written ONE time; briefs
point to it, the check brief gets it by `cat`; (2) the lead reads only exit codes, summary lines
and failed lines of a gate output; (3) a fresh helper conversation when the area changes or after 5
sub-tasks; (4) sub-task gate (type check + that sub-task's tests + lint on its files) after each
sub-task, the full suite only on the base, before the check and after the last round; (5) a repro
test and its fix in ONE helper run; (6) start every Devin run with `~/.claude/skills/multi-model-fix/templates/lean/lean-run.sh`, wait with
`~/.claude/skills/multi-model-fix/templates/lean/lean-wait.sh` (230 s at most per wait: a 5-minute prompt cache must not run out), build the
check brief with `~/.claude/skills/multi-model-fix/templates/lean/lean-mkcheck.sh`; (7) the checker never runs in the helper's worktree.
When the work runs on another machine, copy the scripts there first.

**Third pass (2026-10-08, lean-lane.md B3, B4):** sub-tasks are put in GROUPS by the files they
edit; groups with no common file run at the same time (3 at most), each in its own worktree, on
autopilot with `~/.claude/skills/multi-model-fix/templates/lean/lean-group.sh` (helper, sub-task gate `gate-<step>.sh`, one automatic gate
return, next step); a seam file is its own first group; the lead waits for all groups in one
`lean-wait.sh` call and reads the summaries; `~/.claude/skills/multi-model-fix/templates/lean/lean-collect.sh` joins the groups into one
integration tree for the full gate and the check, and writes the delta after a fix round.


Create a todo per step and work them in order.

## Step 1 — Spec: turn the wish into acceptance criteria

Write **`docs/features/<YYYY-MM-DD>-<slug>.md`** from `templates/spec.md`:

- **Goal** — one paragraph, in the user's words, then one sentence in yours.
- **Acceptance criteria** — numbered, each one **a test somebody could write**: given / when /
  then. "Users can export" is not a criterion. "Given a project with 3 tasks, when the owner clicks
  Export, then a CSV with 3 rows and these 5 columns downloads" is.
- **Out of scope** — what this feature deliberately does not do. Builders drift into it otherwise.
- **Constraints** — what must not change: public interfaces, data, behaviour existing tests pin,
  performance budgets, the design system.
- **Open questions** — anything the criteria cannot be written without.

If there are open questions, **ask the user now** — one message, all questions, with your proposed
answer for each so a "yes" is enough. Use the brainstorming skill's discipline: understand what
they want before deciding how to build it. Do not dispatch a builder against an open question.

If the spec ends up as one criterion touching one file, say so and offer to build it in the
session. This skill is overhead for a one-liner.

## Step 2 — Seams: write the contracts before anyone builds

Read the codebase where the feature lands. Then write, into the spec file, every interface the
parts will share:

- function and method signatures with types, and what each returns on failure;
- data shapes — table columns, JSON fields, event payloads, props;
- routes, commands, hooks, filter names;
- the order things happen in, when it matters;
- which existing code each part calls, and what it may not call.

Each seam gets an owner (the part that defines it) and consumers (the parts that call it).
**Consumers build against the contract, not against the owner's code**, so nobody waits. Where a
seam needs a stub for a consumer's tests to run, the owner's brief says to ship the stub first.

Builders may propose a change to a seam. They may not make one silently. A brief says so.

## Step 3 — Split into parts, by FILE, evenly across models

1. Break the feature into parts. A part is a set of files that one agent can own end to end and
   that maps to one or more acceptance criteria. Name which criteria each part satisfies; every
   criterion must land in exactly one part, or in the integration step by name.
2. **Map the write set of every part.** Two agents editing one file clobber each other and one
   reports success. Files shared by two parts go to one owner; the other part treats them as
   read-only and asks.
3. **Distribute parts as evenly as the file boundaries allow** — twelve files across three models
   is four each, not twelve to one. If the feature is one lump of tightly coupled files, say so
   and offer `2`, or propose a seam that splits it.
4. Assign each part's **reviewer** now: the next model around the ring, never the builder, never
   Claude for Opus, never the same subscription.
5. Write the split into the spec as a table: part → files → criteria → builder → reviewer.

In `dry` mode, show the user the spec, seams and split, and stop.

## Step 4 — Brief and dispatch the builders, one worktree each

Use `templates/build-brief.md`. Every brief carries **the whole spec** (goal, criteria, out of scope,
constraints), **every seam verbatim**, and then the part:

- the acceptance criteria this part satisfies, by number;
- the **exact files it may create or modify**, and the list it must **not** touch — other agents
  are working in the same repo right now;
- the seams it owns (define these first, stub if a consumer needs it) and the seams it consumes
  (call exactly this, do not reimplement);
- the project's conventions to follow — point at an existing file to copy the style of;
- **test first.** For each criterion: write the failing test, paste the red output, implement,
  paste the green output. A criterion with no test is not done, and the brief says so;
- **no `git commit` / `add` / `checkout` / `stash`.** Leave everything in the working tree.
- own `git worktree` on its own branch (`git worktree add ../<project>-mb-<model> -b mb/<date>-<model>`);
- if the part cannot be built without changing a seam or touching a forbidden file: **stop and say
  so**, with the proposed change. Do not improvise around it.
- refusing or scoping down with a reason is a valid outcome. Record it.

Dispatch in parallel. Hard wall-clock cap per run (45 min default for builds), activity-aware
watchdog per sliced-review Step 6. A hung backend must not look like a slow one.

Before dispatching, read `~/.claude/skills/sliced-review/references/runners.md` →
**"Orchestration gotchas"** (never launch a long job with `nohup … &` inside a tool shell — it
detaches, gives no completion notification, and can be killed with the shell; use tracked
background instead; work in a dedicated read-only worktree at the right commit; write into the
synced tree) and **"Gotchas that keep biting — per backend"** + **"Linux laptop"**. These encode
errors we have already made; don't repeat them.

## Step 5 — Review every part with a model that did not build it

Use `templates/review-brief.md`. The reviewer gets the spec, the seams, the part's criteria, the
diff, and the builder's pasted red/green output. It answers, in order:

1. Does each claimed criterion actually hold? Run the tests. Read them — a test that asserts what
   the code happens to do is not a test of the criterion.
2. **What did the builder not test?** The empty list, the second user, the concurrent call, the
   failure path of a seam it consumes.
3. Does it honour the seams exactly, or did it drift?
4. Did it stay in scope and inside its files?
5. Conventions, security, performance — only where the spec's constraints name them.

Verdict: **APPROVE**, **APPROVE WITH REQUIRED CHANGES** (file, line, exact change), or **REJECT**
(which criterion fails, demonstrated). "Looks good" without running anything goes back.

## Step 6 — When it is still not right: adversarial rounds, MAXIMUM THREE

Builder answers, reviewer re-checks. Three rounds, then the disagreement goes to the user stated
plainly, and the rest of the feature keeps moving.

## Step 7 — Integrate: merge, seams, full suite, settled-tree review

1. Merge every builder's worktree into one integration branch, seam owners first.
2. **Walk every seam**: does the consumer call what the owner shipped? Type-check or run the
   integration test for each; a stub left in place is a failure.
3. Any criterion assigned to "integration" is built here, by the session model or the model that
   authored the least.
4. **Full suite on the whole tree.** Per-part green proves nothing about the join.
5. **Settled-tree review**: the complete diff to whichever model authored the **least** of it, on a
   different subscription from the largest author. Files skipped in Step 5 for being mid-edit are
   reviewed here. Nothing is finished while that list is non-empty.

If the suite fails, nothing is committed. Report it.

## Step 8 — The session model approves and commits. Once.

Read the whole diff yourself against the spec. Every acceptance criterion: name the test that
proves it. This is the integration gate and the human-facing decision — **not a third review**.
Then **one commit** (or one PR if the project works on PRs), message naming the feature and the
spec file, then remove the worktrees.

**What still stops the pipeline, in every mode.** A migration that touches existing data, a change
to a public interface the spec did not list, credentials or billing, a seam the builders want
changed after consumers built against it, or a reviewer and builder who still disagree after three
rounds. Those go to the user with the question stated.

## Step 9 — Record, and the report

1. **The spec file** gets its final section: what shipped, per criterion the test that proves it,
   what was scoped out and why, the commit.
2. **`docs/STATUS.md`**, if the project has one: the feature under "Built & live", anything
   deferred under "Open todos".
3. **User-facing changelog**, if the project has one: one row for the feature, written for the
   reader, not the engineer.
4. **Report to the user** — two tables, always:

   | part | files | criteria | builder | reviewer | rounds | tests added | result |

   | model | parts built | approved first pass | required changes | rejected | time |

   | step | model | time | input | cached | output | est. cost |

   (one row per run: scout, each builder, each review, the session model; then a total row; lean-lane.md A5.)

   Then the stops: anything that went to the user unbuilt, and why. Name every UNCHECKED pass.
5. **`report` suffix, or ask once** — "Build the Markdown + HTML build report? (y/n)". Render the
   spec file and the two tables to `docs/features/<date>-<slug>.html` in the same page style as
   sliced-review's `templates/build-report.py`. Never build it unasked.

## Step 10 — `/wrap lite`, unless `no wrap`

## Honesty rules

- Never dispatch a builder against an open question or a missing seam. Ask first.
- Never report a criterion as met without naming the test that proves it, and having run it.
- Never let a model review its own part — and "own" means the model family. Opus is Claude.
- Never let a part and its review sit on the same subscription.
- Never present the session model's approval as an independent review.
- Never give the whole feature to one model without asking. Even split, or the user chooses.
- Never change a seam silently after consumers built against it. Say so, re-brief, re-review.
- Never commit per builder. The tree is only known good after Step 7.
- Never send a reviewer work that the machine gate did not pass.
- Never close a row / part with no change unless a repro test AND the checker agree; else report it as CLOSED UNCHECKED.
- Never leave a later pass (required change, clean-up, merge fix) without its own check, or report it as UNCHECKED.
- Never report a token or cost figure you did not read from a log. `n/a` is a valid cell.
- Never call a feature done while a criterion is unassigned, a stub is in place, or the settled-tree
  list is non-empty.

## Keep the prompt cache warm (added 2026-10-08)

A Claude subagent loses its prompt cache after 5 minutes without a request, and then pays for its
whole context again (about $0.75 each time). So: no tool call of a subagent waits longer than 230
seconds. Start every long run (builder, reviewer, `codex exec`, a long test suite) in the
background and wait in short steps, with the scripts and the rule in
`~/.claude/skills/sliced-review/references/keep-warm.md`. Put this rule in the brief of every
subagent that will wait for a run.
