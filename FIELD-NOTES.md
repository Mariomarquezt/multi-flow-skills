# Field notes — why this skill exists

Measured, not reasoned. Update this file when a run teaches something new.

## 2026-08-16 — three parallel whole-repo lanes returned zero findings

**Target:** an agency SaaS (private repo). **38,415 lines** of non-test source
(`src` 34,322 + `worker` 4,093). **Reviewer:** GLM 5.3 on a z.ai **LITE** plan.

Three review lanes — security, correctness, quality — each told to *"review the whole
repository"*, fired **in parallel** at 00:01 PDT.

| | Before | ~9 minutes later |
|---|---|---|
| 5-hour token window | 0% used | **100% used** |
| Weekly quota | 39% used | **60% used** |
| Findings returned | — | **zero** |

All three died on `HTTP 429`. They never got past reading the codebase. **21% of a weekly
subscription bought nothing at all.**

### What that proves

1. **The exploration is the cost, not the reasoning.** The lanes spent an entire window
   globbing and reading before producing a single sentence of analysis.
2. **A fresh window is not a fitting job.** `glm-usage.sh` had reported `0% used` sixty
   seconds earlier. That meant the window had reset, not that the work would fit. Never
   read a `0%` as headroom.
3. **Parallelism multiplies the waste.** Three lanes did not finish three times faster —
   they each got one third of the way and then all died.

### What was done instead

The same audit was re-cut into **29 slices**, each naming an **explicit file list** (never a
directory tree to explore), capped at ~2,100 lines, ordered by blast radius so that running
out of budget partway still covered every defect class that damages a customer. Runner
enforced one slice at a time with a quota guard and a cost ledger.

Kit: that project's `docs/glm-review/` (private). Reasoning written up in its `docs/STATUS.md`.

## 2026-08-16 — five of twenty-nine file paths were wrong on the first pass

Validating the slice file lists against the repo caught five bad paths: `src/lib/catalog.ts`,
`src/lib/contacts.ts`, `src/lib/memory.ts`, `src/lib/search.ts`, `src/lib/storage.ts` were all
**directories**, not files.

Each would have sent a slice hunting for a file that does not exist — one wasted run apiece,
roughly a sixth of the remaining weekly budget. **Validate every path before committing.**

## 2026-08-16 — not every backend can tell you what is left

GLM has `~/.hermes/glm/glm-usage.sh`, which returns live remaining quota. That is what makes a
pre-flight guard possible.

Kimi has `~/.hermes/kimi/kimi-tokens.sh`, which is a **different thing**: it sums the tokens and
notional cost of a run **that already happened**, from its transcript. It cannot answer "is there
room". Assuming otherwise would produce a guard that never fires.

When a backend cannot report remaining quota, a **429 is the only honest signal**, and the runner's
header must say the guard is absent.

## 2026-08-16 — first measured slice cost, on Kimi K3

**Target:** Formitor, 35,382 lines cut into 41 slices. **Reviewer:** Kimi K3 (`k3-256k`) on a
Kimi For Coding subscription. **Slice:** `t1-01-update-channel`, 851 lines across 3 files —
almost exactly the mean slice size (863).

| | one slice |
|---|---|
| tokens | 195,958 |
| notional USD (K3 list price) | $0.62 |
| wall clock | 4 min 03 s |
| **5-hour window consumed** | **22%** |
| **weekly budget consumed** | **8 points** (56% remaining → 48%) |

Read from the account UI by the user, before and after. The notional dollar figure from
`kimi-tokens.sh` is NOT what a subscription meters on — only the percentages are the real
constraint, and they are 
the only reason this entry is useful.

### What that buys

- **4 slices per 5-hour window** (a 5th needs 110%).
- **12.5 slices per week** — and the WEEK is the binding limit, not the window.
- 41 slices ≈ **3.7 weeks** and ~320% of a week's budget: the plan does nothing else for a
  month.

### The lesson that generalises

**Slicing controls waste; it does not make a metered plan large.** The 29-slice GLM run and
this 41-slice Kimi run are the same technique, but a review that fits comfortably on one plan
can be a month-long commitment on another. Measure the plan, not just the codebase — and
measure it in the units the plan actually meters (percent of window, percent of week), never
in notional API dollars.

Corollary: `runner.env` being the ONLY backend-specific file is worth more than it looked.
When tier 1 deserves the expensive model and tiers 3–4 do not, splitting the queue across two
backends is a one-line edit, and the slices themselves do not change.

### User's hypothesis, now with evidence

"Kimi runs out faster than GLM" — **supported, first evidence.** One 851-line slice took 8
points of the weekly plan. The GLM run has no comparable per-slice weekly figure yet, so this
is one-sided: it establishes Kimi's rate, not the ratio. Measure a GLM slice the same way
before treating the comparison as settled.

### Quality, for the record

That one slice produced 2 findings — a HIGH and a MEDIUM — on code that had already been
through a Codex audit (3 rounds) and a GLM review (2 rounds), both of which missed them. Both
were verified by hand against the source and held up. Expensive, but not empty.

## 2026-08-16 — first measured slice cost, on GLM 5.3 (and it is ~20x cheaper than Kimi)

**Target:** a client's Laravel back-office system (private repo), 45,966 lines cut into 39 slices.
**Reviewer:** GLM 5.3 on a z.ai **LITE** plan. **Slice:** `t1-01-account-scope`, 588 lines
across 7 files — the smallest tier-1 slice.

| | one slice |
|---|---|
| wall clock | 3 min 40 s |
| **5-hour window consumed** | **1 point** (30% -> 31%) |
| **weekly consumed** | **0 visible points** (82% -> 82%) |
| output | 6,854 bytes, 4 findings + a clean-areas section |

### This settles the open question, and reverses the expected direction

Compare the Kimi K3 measurement above: an 851-line slice cost **22% of a 5-hour window** and
**8 weekly points**. A comparable GLM slice cost **1% of a window** and did not visibly move
the weekly meter at all. GLM is roughly **20x cheaper per slice** than Kimi K3 here.

That is the opposite of the whole-repo experience at the top of this file, and it is the
point: the 21%-of-a-week disaster was **the wandering**, not the model. Given an explicit
file list, the same model on the same plan reviews a slice for ~1% of a window.

**The user's hypothesis "Kimi runs out faster than GLM" is now measured on both sides and
CONFIRMED** — but only for sliced runs. Neither figure says anything about unsliced ones.

### Practical consequence

A 39-slice queue that looked like a multi-week commitment fits inside a single LITE plan's
remaining 18% of a week. Do not size a queue against a plan until slice 1 has run: the
estimate here was wrong by more than an order of magnitude, in the *generous* direction.

### Quality, for the record

That slice produced 4 findings on code that had already been through a Codex audit (3
rounds), a GLM whole-repo review (2 rounds) and a Kimi K3 review. Its best finding — an ORM
delete hook that hard-deletes child rows with no force-delete guard, so a soft-deleted parent
row can never be restored intact — was missed by all of them. It also
stated plainly, four times, what it could **not** verify from within the slice. That
self-limiting is a direct product of the "say plainly if you could not verify" rule in
`_context.md`.

## 2026-08-17 — a percent-of-plan figure is worthless without the plan it was read on

**Target:** Formitor. **Reviewer:** Codex `gpt-5.6-sol` at MEDIUM effort. Five tier-1 slices.

| slice | tokens | wall clock |
|---|---|---|
| t1-01 update-channel | 34,250 | 1m32s |
| t1-04 spoke-poll-edge | 50,570 | 2m05s |
| t1-02 spoke-auth-surface | 32,118 | 1m52s |
| t1-05 test-context | 31,679 | 1m38s |
| t1-06 mail-interception | 42,101 | 1m34s |
| **total** | **190,718** | **8m41s** |

Slice one read the Codex weekly meter 0% -> 1%. From that single point the queue was sized at
"41 slices = 41% of a week". Four slices later the meter still read 1%, which looked like the
estimate had been wrong by 4-5x in the generous direction — and it was reported that way.

**It had not. The user had upgraded to a 5x Codex plan in between.** The work cost the same; the
denominator grew. Both readings were honest and the conclusion drawn across them was not.

### The rule this adds

The skill already says to measure in the units the plan meters (percent of window, percent of
week) rather than notional API dollars. That is still right, and it is not enough:

**A percent is a ratio, and the denominator is a subscription tier that a human can change at any
moment without telling you.** So:

- **Record the plan tier beside every percentage.** "1% of a 5x Codex weekly" is a fact. "1% of
  the weekly" is a fact with a hole in it.
- **Never derive a rate from two readings taken at different times** unless you know the tier did
  not move between them. A flat meter across four slices is equally well explained by cheap
  slices and by a bigger plan.
- **Tokens and wall clock are plan-invariant. Prefer them for anything that has to survive.** The
  190,718 figure above is still true on any tier; every percentage in this file is only true on
  the tier it was read on.

Kimi's 8-weekly-points-per-slice and GLM's 1%-per-slice entries above were both read on a single
unchanged plan, so they stand — but neither says which tier, and both should be read as "on the
plan in use that day", not as a property of the model.

## 2026-08-17 — a hung backend never errors, and bills for nineteen hours

**Backend:** `qwen3.8-max` via OpenCode Go. **Slice:** `t1-01-update-channel`, ~20 KB prompt.

| attempt | variant | duration | output | provider cost counter |
|---|---|---|---|---|
| 1 | medium | 38m 31s | 268 bytes | +$1.85 |
| 2 | minimal | **19h 37m** | **32 bytes** | **$8.18 -> $18.12** |

Both runs printed the backend's banner line and then nothing. Neither returned an error, produced a
persisted session, or tripped any guard in the kit. A one-sentence smoke test on the SAME model
answered instantly, so the model and the plan were both healthy — it stalls on a large prompt
specifically, and stalls *silently*.

The cost counter is account-wide, so not every cent is provably qwen's; qwen was the only process on
that plan for essentially the whole window.

### Why every existing guard missed it

The 429 check, `SUSPICIOUSLY_SHORT`, the pre-flight quota gate and the `MAX_HOURS` chain deadline all
trigger on something the backend **did**. A hang does nothing. `SUSPICIOUSLY_SHORT` would have caught
it — *after* the run returned, which it never did.

### The fix, now in the template

`run-slice.sh` now watches two things. `SLICE_IDLE_TIMEOUT` (600s) kills a run that has written
NOTHING NEW for that long — activity-aware, so a slow-but-streaming backend is never touched however
long it takes. `SLICE_TIMEOUT` (1200s) is an absolute backstop for a backend that emits steady noise
while making no progress. Both kill the **process group**, because these backends spawn children
that outlive the wrapper and keep billing unparented, and both record a distinct status
(`KILLED_IDLE` / `KILLED_TIMECAP`) rather than letting a signal death read as `EXIT_137` — an
ordinary-looking crash a tired reader waves through.

Verified both directions on stubs: a run writing steadily for 24s survived a 6s idle cap; a run that
printed a banner then slept was killed at 10s, with zero orphaned children. The first pass at this
was a plain wall-clock cap that would have killed a legitimately slow slice — Mario caught that in
review before it shipped.

**The omission was in a hand-written driver loop, not in `chain.sh`.** Ad-hoc loops written to
parallelise a run are exactly where this reappears. If you write one, give it the same cap.

## Open questions

- [answered 2026-08-16 for Kimi K3 AND GLM 5.3 — see above] Cost per slice. Still unmeasured
  for Command Code and Codex. Measure each the same way: read the plan's own percentage before
  and after ONE slice, because notional API dollars do not track a subscription's meter.
- [answered 2026-08-16] "Kimi burns faster than GLM" — CONFIRMED for sliced runs, by ~20x.
  Kimi K3: 22% of a window / 8 weekly points for 851 lines. GLM 5.3: 1% of a window / no
  visible weekly movement for 588 lines. Says nothing about unsliced runs.
- Does slice cost scale with lines, or is there a large fixed cost per run? One data point
  cannot tell these apart. A short slice and a long one, measured back to back, would.

## 2026-08-20 — a whole 20k-line codebase reviewed for 4% of a GLM LITE week

**Target:** a live language-learning app (private repo). **19,916 lines** of non-test source
(convex 5,506 + src/app 3,843 + src/components 9,199 + src/lib 850 + scripts 310 + a few
top-level files), cut into **18 slices**. **Reviewer:** GLM 5.3 on a z.ai **LITE** plan.

| | whole queue |
|---|---|
| slices run | 18 of 18 |
| lines covered | 19,916 |
| wall clock | 1h 29m |
| mean per slice | 4m 28s, 6,047 bytes |
| **weekly consumed** | **4 points** (95% -> 99% used) |
| 5-hour window | ~1 point per slice |
| 429s | **zero** |
| watchdog kills | **zero** |
| findings | 8 HIGH, 30 MEDIUM, 44 LOW |

**The queue started with 5% of the week left and finished the entire codebase inside it.**
The user's instruction was "use that to the limit and we'll continue in a couple hours once
the limits renew" — the review finished before the limit did.

### What this confirms and what it adds

It confirms the 2026-08-16 GLM entry (~1% of a 5-hour window per slice, weekly barely moving)
and extends it from one slice to eighteen. **Per-slice weekly cost held at ~0.22% across the
whole run** — 95->96 at slice 5, 96->97 at slice 9, 97->98 at slice 13, 98->99 at slice 16.
The rate was linear, which is what makes the projection trustworthy here and did not exist
from a single point.

It also answers a standing open question, partially: **slice cost did not track lines.** The
smallest slice (427 lines) and the largest (1,898) both cost about the same wall clock and
about the same meter movement. On GLM with an explicit file list, the per-run fixed cost
dominates. Practical consequence: **do not shrink slices below ~1,500 lines on this backend to
save budget — it buys nothing and costs review coherence.** Slices 1-10 averaged 695 lines and
were probably too small.

### The plan-tier trap, avoided this time

`glm-usage.sh` reported the 5-hour window at **0% used** and the weekly at **95% used** in the
same breath. A `QUOTA_PCT_CMD` written from `references/runners.md` reads only the 5-hour
line — it would have reported full headroom with 5% of the week left. The adapter used here
prints the **higher of the two**, so whichever limit is tighter is the one that guards. Any
backend with two nested windows needs that; reading only the inner one is the same class of
error as the 5x-Codex-plan entry above.

### Method note worth keeping: a handoff is cheaper than a re-run

One UI slice (`t4-11-app-gated-routes`) raised two HIGHs and a MEDIUM that were all explicitly
framed as *"Convex slice: verify X"* — it could not see the server and refused to clear it.
All three were already answered by slices 1, 2 and 6. **Resolving them cost zero runs: two
reports read side by side.** The `_context.md` rules "report only what you can point at" and
"say plainly if you could not verify" are what produced that shape instead of three confident
wrong findings.

### Quality, for the record

The codebase had already been through a Codex audit, a prodgate assessment of 30 items, and a
20-tip T0 pass. The sliced review still found, hand-verified: a rate-limit counter written on only one
branch, turning a quiz path into an unlimited answer oracle; an admin save whose empty
`.catch()` shows a success toast on a rejected write, silently discarding the author's work;
and a seed `--overwrite` that deletes and re-creates every content row, orphaning every user's
history. Grepping the prior-audit file confirmed none of those three appear anywhere in it.
(Specifics withheld here until fixed.)

**Correction, same session:** the review's other hand-verified HIGH — an authentication
weakness on one HTTP route — WAS already on the board, under `owasp-a02`, described in more
detail than the review gave it. It was reported to the user as new before the
prodgate file was grepped. The lesson is procedural and belongs in the skill: Step 7 says to
fold prior findings into the briefs as a "do not re-report" list, and a `.prodgate.yml` (or any
machine-readable prior audit) is exactly that input. Here the STATUS.md open-todos were folded
in and the 28KB of prodgate `evidence:` prose was not — so one slice spent budget rediscovering
a known finding, and the write-up overclaimed novelty until the file was checked. **Grep the
prior-audit artifact for each finding before calling it new.**
