---
name: multi-flow
description: Our own end-to-end build flow for a NEW project — interview, multi-model plan, spec, tickets, multi-model build, multi-model review, multi-model fix, wrap. It chains grill-with-docs, to-spec and to-tickets (Matt Pocock's skills, called as they are, never edited) with our four skills (multi-plan, multi-build, sliced-review, multi-fix) and runs `/wrap lite` after each of ours. Use when the user says "/multi-flow", "new project from start to finish", "run the whole flow", or starts a new app and wants every phase governed. NOT for one step alone (use that step's skill) and NOT for fixing a single bug.
disable-model-invocation: true
---

# Multi Flow

Build a project from an idea to reviewed, fixed, committed code in one governed run.
This is OUR skill. It is the multi-model sibling of Matt Pocock's `full-build` (we do not edit his).

**Two rules that keep it ours:**
1. **Matt's skills are called, never copied or edited** — `grill-with-docs`, `to-spec`, `to-tickets`
   (and `setup-matt-pocock-skills`). An upstream update would erase any change. If we ever write
   our own `to-spec` or `to-tickets`, we swap the name in the phase table below and nowhere else.
2. **Model versions live in ONE file:** `~/.claude/skills/_shared/models.md`. This skill never names
   a model version. Say "Sol", "Grok" — read the exact id from that file.

**The one idea:** state lives in `.multiflow/STATE.md` and git, never in the conversation. Every
phase ends by writing state. A fresh agent reads state and continues.

## The phases (one todo per phase; never start one before the one before it is done)

| # | Phase | Skill it calls | Whose | After it |
|---|---|---|---|---|
| 0 | Preflight | `setup-matt-pocock-skills` (only if no tracker yet) | Matt | — |
| 1 | Interview | `grill-with-docs` | Matt | — |
| 2 | Plan (stack, layout, risks) | `multi-plan` (mode `3`) | ours | `/wrap lite` |
| 3 | Spec | `to-spec` | Matt | — |
| 4 | Tickets | `to-tickets` | Matt | — |
| 5 | Build | `multi-build` (mode `3`), one run per ticket or frontier batch | ours | `/wrap lite` |
| 6 | Review | `sliced-review` (mode `3`, no `fix`) | ours | `/wrap lite` |
| 7 | Fix | `multi-fix` (mode `3`), fed by the review's `findings.json` | ours | `/wrap lite` |
| 8 | Close | `wrap` (full) | ours | — |

## Phase 0 — Preflight
1. Must be a git repo. If not, stop and ask. Create a working branch. Never run on the default branch.
2. No issue tracker + triage labels configured? Invoke `setup-matt-pocock-skills` first (Phases 3–4 need it).
3. Write `.multiflow/STATE.md` from the template in [`REFERENCE.md`](REFERENCE.md).
**Done when:** STATE.md exists, names the branch and tracker, every phase row is `[ ]`.

## Phase 1 — Interview
Invoke `grill-with-docs`. Do not summarise the interview as the spec — Phase 3 does that.
**Done when:** every question is answered, ADRs and glossary are written; list their paths in STATE.

## Phase 2 — Plan with the models
Invoke `multi-plan` (mode `3`) with the interview's output as the idea. It drafts the layout, has
critics attack it, rules on every finding, and ends with the agreed layout + "open fights".
**The user settles the open fights** before moving on. Record the agreed layout path and the
decision-log path in STATE.
Then run `/wrap lite`.
**Done when:** the layout is agreed, open fights are settled, wrap lite ran.

## Phase 3 — Spec
Invoke `to-spec`. Give it the interview AND the agreed layout; it must not re-interview.
**Done when:** the spec is at the path/issue in STATE, names the test seams, and the user confirmed the seams.

## Phase 4 — Tickets
Invoke `to-tickets` against the spec. Output is a dependency graph with blocking edges. Never flatten it.
Copy the `blocked by` column into STATE verbatim — never re-derive it.
**Done when:** the user approved the breakdown and every ticket is in STATE with number, blockers, status `[ ]`.

## Phase 5 — Build (our `multi-build`)
Work the **frontier**: tickets whose blockers are all `[x]`, lowest number first. Each `multi-build`
run takes **one ticket** (or a batch of frontier tickets that touch different files).
- **The ticket IS the spec.** Hand `multi-build` the ticket text as its frozen spec. Its Step 1 then
  only checks the acceptance criteria are testable; it does not rewrite them. Its Steps 2–8
  (seams, split by file, builders, cross-review, integrate, one commit) run as written.
- One commit per ticket run, message names the ticket number. Commit BEFORE ticking STATE.
- After EACH `multi-build` run: `/wrap lite` (it runs by default — do NOT pass `no wrap`).
**Done when:** every ticket row is `[x]` with a commit hash and the full suite passes once.

## Phase 6 — Review (our `sliced-review`)
Invoke `sliced-review` mode `3` over the built code. Read its FIELD-NOTES before the first run;
do not restate its slicing or ledger rules. Keep `findings.json` and the triage output under
`.multiflow/review/`. Then `/wrap lite`.
**Done when:** the review finished, triage is done, `findings.json` is saved.

## Phase 7 — Fix (our `multi-fix`)
1. **You read every confirmed finding yourself** and mark it `fix`, `defer` or `reject` with a one-line
   reason. A reject needs evidence, not an opinion.
2. Invoke `multi-fix` mode `3` on the `fix` set. HIGH first as its own run; MEDIUM and LOW may share one.
3. Re-run the full suite and typecheck. Read the diff like a contributor PR.
Then `/wrap lite`.
**Done when:** the suite is green and every HIGH is fixed with a proving test or deferred in STATE with a reason.

## Phase 8 — Close
Invoke `wrap` (full mode). **Done when:** wrap finished and STATE shows every phase `[x]`.

## Rules for chaining our four skills
- `/wrap lite` runs at the end of each of our four skills by default. In this flow, leave it ON
  between them. Pass `no wrap` ONLY on the run right before Phase 8, because Phase 8 does the full wrap.
- Each of our skills reads models from `_shared/models.md`. Do not override a model here.
- `report` mode is off unless the user asks.

## Resuming after a reset
Read `.multiflow/STATE.md` and the last five commits. Pick the first unticked phase — inside Phase 5,
the lowest-numbered ticket whose blockers are all `[x]`. Do not re-read the conversation. Do not redo ticked work.

## Red flags — stop
- About to edit a Matt skill (`to-spec`, `to-tickets`, `grill-with-docs`) → don't. Change THIS file's phase table instead.
- About to write a model version into this file → put it in `_shared/models.md`.
- About to start a ticket whose blockers are not all `[x]` → it is not on the frontier.
- About to tick a ticket before its commit exists → commit first.
- About to skip `/wrap lite` between our skills → run it.
- About to start Phase 7 without reading every finding yourself → read them.
- About to run Codex through the `codex:codex-rescue` subagent → banned. Use `multi-build`'s own Codex route.

## Keep the prompt cache warm
Same rule as our other skills: no subagent tool call waits longer than 230 seconds. See
`~/.claude/skills/sliced-review/references/keep-warm.md` and put the rule in every subagent brief that waits.
