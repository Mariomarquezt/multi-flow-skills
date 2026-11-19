---
name: multi-plan
version: 1.1.0
description: Turn an idea into a build plan with several models — the session model writes the first full draft (goal, stack, architecture, data model, phases, risks, cost), then other models on other subscriptions do ADVERSARIAL review of it independently, the session model rules on every finding (accept / partial / reject / defer to the user) and revises, and the loop repeats up to 3 rounds or until no BLOCKER/MAJOR change is left. Ends with the agreed layout, a decision log, and the "open fights" only the user should settle. Use when the user says "/multi-plan", "plan this with the models", "have the models argue the stack", "multi-model plan", "get the other models to review my plan", or gives an idea and wants the best stack agreed before building. MODES: `2` = Sol + Grok critics; bare or `3` = Sol + Grok + DeepSeek Flash; `5` = Sol + Grok + DeepSeek Flash + GLM Flash + MiniMax Flash; `fast` = Composer + DeepSeek Flash, 1 round; `rounds N` caps the loop (1–3); `dry` = draft v1 only, no critics; `report` = also publish an HTML report. NOT for building (hand the final plan to /multi-build or /codex-build), NOT for reviewing code (/sliced-review, /code-review), NOT for a one-person grilling of the user (/grilling).
---

# Multi-plan

> **Model names are short names.** The exact version of each lives in ONE place:
> `~/.claude/skills/_shared/models.md`. Read it before the first dispatch and
> write the exact model id in the final layout. Grok here = the **Grok** row (4.6, reviews).
>
> **Gemini (Antigravity, added 2026-11-17):** Gemini Hydrogen / Carbon / Argon / Flash are in models.md as extra
> lanes — no mode uses them until the user moves them in. Swap one in only when the user asks. Runner:
> `$RUNNERS_DIR/antigravity/agy-run.sh` (read-only: critics never get `--write`). One Gemini lane never checks another Gemini
> lane's work; Gemini Flash on Antigravity and on Cursor is one model.
>
> **Model rules (repo owner):** every Claude part runs on Opus 5.5 — never Fable, never
> Opus 5 or older. **Never OpenRouter** unless the user names it or approves it for THIS task.
> State both rules in any handoff this skill writes.

One idea. I write the plan. The other models attack it. I decide what changes. Up to three times.

## The one idea

A plan written by one model carries that model's habits: its favourite stack, its blind spots,
its guesses about prices and limits. Other models, on other bills, trained by other labs, attack
it **independently** — none sees another's answer in the same round — so their agreement means
something. The session model stays the **author and editor**: it does not obey the critics, it
rules on each point in writing, and a critic that loses can appeal once with new evidence. The
loop stops when the critics run out of serious objections, not when a round count is hit.

The session model never critiques its own plan, and no critic is Claude.

## Modes — parse the invocation FIRST, state it back in one line

| invocation | critics | max rounds |
|---|---|---|
| `/multi-plan 2` | Sol (Codex), Grok (Cursor) | 3 |
| `/multi-plan` or `/multi-plan 3` | Sol, Grok, DeepSeek Flash (provider picked) | 3 |
| `/multi-plan 5` | Sol, Grok, DeepSeek Flash, GLM Flash, MiniMax Flash | 3 |
| `/multi-plan fast` | Composer (Cursor), DeepSeek Flash | 1 |
| `… rounds N` | — | N (1 to 3) |
| `… dry` | none | 0 — draft v1, show it, stop |
| `… report` | — | — also publish the HTML report (Step 7) |

Compose freely: `5 rounds 2 report`, `fast report`.

**Independent eyes.** Two routes of ONE model count as one critic. Grok and Composer share the
Cursor pool, so `fast` pairs Composer with DeepSeek Flash, never with Grok. DeepSeek Flash and GLM
Flash may land on the same provider; that is fine for plan review (they are different models) but
write the provider of each in the decision log.

**Router (suggest mode).** Before Step 3, run:

```sh
$RUNNERS_DIR/router/router suggest --task "<one-paragraph idea summary>" --items 1 --mode fix --n <critics>
```

(The router has only `fix` and `build` modes — no `review`. `fix` is the closest: it ranks
arms by how well they find and judge problems.)

State its pick next to the mode's default in the mode line. Keep the default unless a default
arm's plan is BLOCKED or near empty — then take the router's substitute and say so. If the router
errors, carry on with the default and note it. After the last round, log one outcome per critic
(`router outcome --id … --arm … --role reviewer --result pass|fail`, `--found <accepted findings>`).

## Where the files go

- In a project folder: `docs/plans/<YYYY-MM-DD>-<slug>/`.
- Otherwise: `~/Desktop/Claude/plans/<YYYY-MM-DD>-<slug>/`.

```
plan-v1.md, plan-v2.md, …     each version, never overwritten
round-<R>/brief.md            the exact brief the critics got
round-<R>/<arm>.md            each critic's raw answer (+ .transcript)
decisions.md                  the ruling on every finding
plan-final.md                 the agreed plan (copy of the last version, plus §11 below)
```

Create a todo per step and work them in order.

## Step 1 — Intake

Read the idea. If anything the stack depends on is missing — who uses it and how many, budget,
hosting the user already pays for, systems it must fit with, deadline — ask **one message, at
most 4 questions, each with my proposed answer** so a "yes" is enough. Read the project's
STATUS.md / CLAUDE.md first if the idea lands in an existing project; do not ask what the files
already say. Do not ask about taste the critics can argue.

If the idea is tiny (one script, one page, one obvious stack), say so and offer a plain plan in
the session instead. This skill costs several model runs.

## Step 2 — Draft v1

Write `plan-v1.md` from `templates/plan.md`. Fill every section. The stack table names a
runner-up for each layer and why it lost — this gives the critics something concrete to attack.

Check facts the picks rest on (current versions, prices, free-tier limits) with a quick web
search when unsure, and tag each row `[fact]` or `[hypothesis]`. Never write a credential into
the plan.

`dry` mode: show v1 and stop.

## Step 3 — Critic round R

1. Copy `templates/critic-brief.md` to `round-<R>/brief.md`. Paste the WHOLE current plan and,
   from round 2 on, every row of `decisions.md` so far. Fill round and max.
2. Run every critic **in parallel**, read-only, one background Bash call:

   ```sh
   S=~/.claude/skills/multi-plan/scripts/critic.sh; D=<plan dir>/round-<R>
   for a in <arms>; do "$S" "$a" "$D/brief.md" "$D/$a.md" & done; wait
   ```

   Arms: `sol grok deepseek glm minimax composer qwen mimo`. The script picks the provider for
   multi-provider models (tokens that expire first), never uses OpenRouter, and never uses Devin
   unless `PROVIDER=devin` is set by the user. Expect 2–10 minutes; run it with
   `run_in_background` and wait for the notice — do not poll.
3. A critic that fails (non-zero exit, empty file, no `VERDICT:` line): rerun it once. If it
   fails again, go on without it and say so in the round summary. Never fill its place with a
   Claude subagent: Claude is the author.

## Step 4 — Rule on every finding

Read all answers. Then, in `decisions.md`:

1. **Merge duplicates.** Same point from several critics = one row, all ids listed, `backers` =
   how many independent critics raised it.
2. **Rule on each row:**
   - **ACCEPT** — change the plan as asked.
   - **PARTIAL** — change part of it; the reason says which part and why not the rest.
   - **REJECT** — one-line reason that answers the critic's `why`, not "I prefer X".
   - **DEFER-TO-USER** — a real trade-off that depends on the user's priorities (cost vs speed,
     lock-in vs convenience). Goes to "open fights".
3. **Weight rules:**
   - A point raised by 2+ critics is ACCEPT unless I can state a concrete reason it is wrong.
   - A BLOCKER is never rejected without a written reason that a reader could check.
   - A `confidence: low` fact claim is checked (web search) before it changes the plan.
   - An APPEAL with no new argument is REJECTED as "no new evidence"; with new evidence it is
     ruled again from scratch.
   - A finding that breaks a constraint the user set is DEFER-TO-USER, not ACCEPT.
4. Tell the user a 3–5 line round summary: verdicts (e.g. "Sol CHANGE, Grok SHIP, DeepSeek
   CHANGE"), accepted / rejected / deferred counts, the biggest change.

## Step 5 — Revise

Write `plan-v<R+1>.md` with every ACCEPT and PARTIAL applied. Fill "Changes from the last
version", one line per change with its finding id. Do not sneak in changes no finding asked for;
if I spot something myself, add it as my own row in `decisions.md` (id `R<R>-AUTHOR-n`).

## Step 6 — Loop or stop

Stop when ANY of these is true; otherwise go back to Step 3 with the new version:

- every critic said `SHIP`;
- this round produced no accepted BLOCKER or MAJOR (only MINORs, or everything rejected);
- the round cap is reached (3 by default).

Say which rule stopped it.

## Step 7 — The agreed layout

Write `plan-final.md` = the last version plus a section **11. How this plan was agreed**:
critics and exact model ids, rounds run, the stop rule, counts of accepted / rejected / deferred,
and any critic that failed.

Then show the user, in this order:

1. **The stack** — the final stack table (layer, pick, one-line why).
2. **The architecture and phases** — short.
3. **What the critics changed** — the 3–7 biggest changes from v1, each with who pushed it.
4. **Where they still disagree** — rejected points that 2+ critics still backed at the end, with
   my reason, so the user can overrule me.
5. **Open fights — your call** — every DEFER-TO-USER row: the trade-off in one line, my pick.
   At most 3; if more, keep the 3 with the biggest cost or lock-in effect and list the rest by id.
6. **Next step** — the command to build it: `/multi-build` (several parts) or `/codex-build`
   (one builder from a frozen plan), with the path to `plan-final.md`.

`report` mode: load the artifact-design skill and publish an HTML page with the same six parts,
plus a round-by-round table of verdicts and the full decision log. Private by default.

## Step 8 — Close

- Log router outcomes (see Router above).
- Write the vault session log per CLAUDE.md (what was planned, the final stack, open fights).

## Honesty rules

- Never report "the models agreed" on a point a critic disputed. Agreement = no live objection.
- Quote critic positions from their files; do not paraphrase a REJECT into a soft "noted".
- If fewer than 2 critics answered in a round, say the round is weak and offer to rerun.
- The plan is a plan: prices, limits and versions tagged `[hypothesis]` stay tagged in the final.
