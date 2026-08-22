---
name: sliced-review
description: Run a full code review of an existing project through another model by splitting the codebase into scoped slices with explicit file lists, ordered into tiers by blast radius, and driving them one at a time with a cost ledger and an optional quota guard. Works with any connected backend (GLM, Kimi, Command Code models, Codex, Claude subagents, or a custom command) and any project size or language — it scales from a three-slice pass on a small repo to a forty-slice queue that runs unattended overnight. Use when the user asks to "review the whole codebase with <model>", "audit this project with a second model", "get a second opinion on this code", "the review keeps running out of credits", "split the review into slices/tiers", or "do the same review we did for <other project>". Also use when a whole-repo review prompt has already died on a 429 and returned nothing, or before a launch or handover on anything high-stakes. NOT for reviewing a plan before code exists (use /grill-me-codex or /codex-review). NOT for reviewing a single diff, branch or PR (use /code-review).
---

# Sliced Review

Review a whole codebase with another model, without the budget being spent on the model wandering
around the repository.

> **Read the evidence first:** [`FIELD-NOTES.md`](FIELD-NOTES.md) — one page, and the entire reason
> this skill exists.

## The one idea

**The cost is in the wandering, not the thinking.**

A prompt that says *"review this repository"* makes the model glob, grep and read its way across
everything before it reasons about anything. That is where the budget goes, and on a metered plan it
can return literally nothing. A prompt that says *"read exactly these twelve files, never run a
repo-wide grep"* costs a fraction and returns findings.

This holds on a generous plan too — it just shows up as a slower, vaguer review instead of a failed
one. Everything below follows from that single fact.

## Create a todo per step and work them in order

---

## Step 1 — Target, reviewer, scale

Settle three things before touching anything.

**The project.** If the user named one, use it; otherwise the current directory. If `docs/STATUS.md`
or equivalent exists, read it first — it says what is already known broken, which stops you spending
a slice rediscovering it.

**The reviewing models — THREE by default.** Claude, Grok and Sol each review independently
(Step 11). Ask only if the user wants fewer, or names a different set. Any connected backend works — a metered
subscription, a pay-as-you-go API, a local model, or a Claude subagent. See
[`references/runners.md`](references/runners.md) for the ones already wired on this machine, their
exact invocation, their known traps, and whether each can report remaining quota. If the user names
a model that is not listed there, `references/runners.md` also has the four questions you need to
answer to wire a new one.

**Whether that model can report remaining quota.** State the answer in one line. It changes Step 6,
and nothing else.

---

## Step 2 — Measure the codebase. Do not estimate it.

Everything downstream is derived from a real number, so get the real number. Adapt the extension
list to the languages actually present:

```bash
cd <project-root>
EXT='-name *.ts -o -name *.tsx -o -name *.js -o -name *.py -o -name *.php -o -name *.go
     -o -name *.rb -o -name *.rs -o -name *.java -o -name *.cs -o -name *.swift -o -name *.kt
     -o -name *.sql -o -name *.sh -o -name *.html -o -name *.vue -o -name *.svelte'
SKIP='-path */node_modules/* -o -path */vendor/* -o -path */.venv/* -o -path */dist/*
      -o -path */build/* -o -path */.next/* -o -path */target/* -o -name *.min.*'
for d in <candidate areas>; do
  [ -d "$d" ] || continue
  l=$(find "$d" -type f \( $EXT \) ! \( $SKIP \) ! -name '*.test.*' ! -name '*_test.*' \
        -exec cat {} + 2>/dev/null | wc -l | tr -d ' ')
  n=$(find "$d" -type f \( $EXT \) ! \( $SKIP \) ! -name '*.test.*' ! -name '*_test.*' \
        | wc -l | tr -d ' ')
  printf "%-28s %8s lines %6s files\n" "$d" "$l" "$n"
done
```

**Sanity-check every number that looks wrong.** A vendored bundle, a `.venv`, a `prototypes/` folder
or generated output will inflate an area tenfold and wreck the plan. If one area is an order of
magnitude above the rest, find out why before continuing.

**Note single enormous files.** A 4,000-line dashboard HTML or a 1,200-line action file will not fit
one slice. Those get sliced **by region within the file** — say so explicitly in the brief
(`read only lines 1–600 of X`).

Present the table to the user. It is the justification for everything that follows.

---

## Step 3 — Scale the plan to the project

The shape of the work changes with size. Pick the band from the measured total, and say which band
you picked and why.

### Small — under ~5,000 lines

Do **not** build a queue and a chain for this. Overhead would exceed the work.

- **2–4 slices**, still ordered by blast radius.
- Run them by hand, one at a time, reading each result before the next.
- Skip `chain.sh` and `queue.txt` entirely. Keep `_context.md` and the slice briefs — those are what
  make the review good, not the machinery.
- Still keep a ledger line per run if the backend is metered.

### Medium — ~5,000 to ~20,000 lines

- **6–15 slices**.
- Build `run-slice.sh`. Build `chain.sh` only if the backend is metered or the user wants it
  unattended.
- Usually finishes in one sitting.

### Large — over ~20,000 lines

- **20–45 slices**. The full kit: context, briefs, queue, runner, chain, ledger, ORDER.md.
- Assume it spans several sittings or an unattended overnight run.

### Slice size within the band

| Reviewing model's budget | Target lines per slice |
|---|---|
| Generous, pay-as-you-go, or local | ~2,000–2,500 |
| Metered subscription, untested | ~1,500 |
| Known to burn fast | ~1,000–1,200 |

Divide the measured total by the target to sanity-check the slice count against the band above. If
the two disagree wildly, trust the line count and say so.

**Do not tune this by feel later.** Step 8 replaces the guess with a measurement.

---

## Step 4 — Map the trust boundaries before drawing any lines

Slices follow **blast radius**, not the directory tree. So first find out where the damage lives.

- If `graphify-out/` exists in the project, **query it** — `graphify query "where does <X> cross a
  tenant boundary"` is far cheaper than grepping, and it is what the directory is for.
- Otherwise skim for: the authentication/authorization layer, anything keyed on an id the caller
  supplies, stored credentials, anything that writes to someone else's system, anything reachable
  without a login, and the concurrency surface (queues, schedulers, workers, cron).

Multi-runtime projects (a plugin + edge functions + a worker + a browser dashboard) get sliced
**across** the runtimes by boundary, not one slice per runtime.

Then name the worst-outcome class **for this specific project** in one sentence and write it into
the shared context in Step 5. It is what the reviewing model will optimise for, so get it right:

- Multi-tenant SaaS → *one customer's data, token or publish target reaching another customer.*
- Single-tenant internal tool → *an unauthenticated path to data or a destructive action.*
- A library → *a caller silently getting a wrong result they cannot detect.*
- A CLI or script → *destroying or corrupting user data with no undo.*
- An e-commerce or billing path → *charging the wrong amount, twice, or not at all.*

If none fit, write the one that does. Do not default to the SaaS sentence out of habit.

---

## Step 5 — Write the shared context and the slice briefs

Create `docs/<model>-review/` in the project (e.g. `docs/glm-review/`, `docs/kimi-review/`).

**The shared context** — copy [`references/templates/_context.md`](references/templates/_context.md)
and fill in the marked blanks. Keep every rule already in it, especially:

- *read only the files listed; never run a repo-wide grep or glob*
- *report only defects you can point at with file:line*
- *try to disprove it before reporting; if the check exists elsewhere in the call path, do not report it*
- *say plainly if you could not verify something*
- *no rewrites of working code, no style preferences, no padding*

**Each slice brief** contains:

1. A one-line title naming the boundary or subsystem.
2. `Read exactly these files:` followed by explicit paths, one per line. A directory is allowed only
   when it is genuinely small and every file in it is in scope.
3. A numbered question set **specific to that code**. "Does every action verify the row belongs to
   the caller's tenant?" beats "check for security issues". Generic questions get generic findings.
4. Where useful, one line permitting a single named file to be opened to follow a call, with
   *"but do not audit it here"*.
5. An **"already reported, do not re-report"** list — see Step 7.

Name files so the order is visible: `s01-auth.md`, `a05-actions.md`, `c11-external.md`, `q20-tests.md`.

### Validate every path before you commit anything

Non-negotiable. A wrong path costs a whole run.

```bash
D=docs/<model>-review/slices
grep -ohE '^[A-Za-z0-9_.][A-Za-z0-9_/.\[\]-]*(\.[a-z]+)?/?$' $D/*.md \
  | sed 's|/$||' | sort -u | while read p; do [ -e "$p" ] || echo "MISSING: $p"; done
```

Tune the pattern to the project's path shapes. On the first real use of this skill five paths were
wrong — directories written as if they were files. Every one would have burned a run.

### Then re-measure the slices

Print lines-per-slice for the whole set. Anything over target gets split. Show the user the table.

---

## Step 6 — Build the runners

For a **small** project, skip to Step 7 and run the briefs by hand.

Otherwise copy from [`references/templates/`](references/templates/):

- `run-slice.sh` — runs **exactly one** slice, optional quota guard, records cost to `ledger.tsv`.
- `chain.sh` — works the queue unattended, saving each report before starting the next.

Then write `runner.env` beside them. It is the only file that changes per backend:

```bash
# What actually runs the model. {PROMPT_FILE} is substituted with a path to the prompt.
# The prompt TEXT is never substituted into this string — slice briefs contain backticks
# and $(...), and the runner eval-expands this line.
RUNNER_CMD='~/.hermes/glm/glm-run.sh "$(cat {PROMPT_FILE})"'

# OPTIONAL. Must print ONE integer 0-100 = percent of the window already used.
# Leave empty when the backend cannot report remaining quota.
QUOTA_PCT_CMD=''

# OPTIONAL. Runs AFTER a slice and prints its cost, for the ledger.
COST_CMD=''

# OPTIONAL. Only for backends whose cost report is CUMULATIVE and all-time, with no per-run
# view. Read before AND after, and the delta is the slice's real cost.
COST_BEFORE_CMD=''

MAX_PCT=60        # refuse to start a slice above this (ignored if QUOTA_PCT_CMD is empty)
SLICE_IDLE_TIMEOUT=600   # kill after this long with NO new output. The real hang detector.
SLICE_TIMEOUT=1200       # absolute backstop regardless of activity. Never disable it — see below.
```

### Every run is watched, and the watchdog is activity-aware

Two limits, because they answer different questions:

- **`SLICE_IDLE_TIMEOUT` (default 600s)** — kills a run that has written **nothing new** for that
  long. This is the real hang detector. A backend still streaming tool calls or report text keeps
  resetting the clock and is **never touched, however long it takes**. A slow-but-working slice is
  safe.
- **`SLICE_TIMEOUT` (default 1200s / 20 min)** — absolute backstop regardless of activity, for a
  backend that emits steady noise while making no progress.

Killed runs are recorded as `KILLED_IDLE` or `KILLED_TIMECAP` — never as a report, never in
`done.txt`.

**Honest limit of the idle check:** a backend that BUFFERS all its output and writes one block at the
end is indistinguishable from a hang while it works. None of the measured backends do this — codex
and opencode both stream — but if you wire one that does, raise `SLICE_IDLE_TIMEOUT` above its
expected runtime, or set it to `0` to disable idle detection and rely on the hard cap alone.

**A backend that fails by HANGING is the most expensive failure mode there is.** It never errors, so
nothing alerts, no retry fires, and the meter keeps running. Every other guard in this kit — the 429
check, the `SUSPICIOUSLY_SHORT` check, the quota gate — triggers on something the backend *did*. A
hang gives you nothing to trigger on.

Measured 2026-08-17: `qwen3.8-max` sat on ONE slice for **19h37m**, produced **32 bytes** — its
banner line and nothing else — and the provider's cost counter rose **~$9.94** in that window. It had
already hung once at a different reasoning variant. Neither run ever returned an error, and neither
would have stopped on its own.

Two details in the implementation matter and should not be simplified away:

- **It kills the process GROUP, not the wrapper.** These backends spawn node and python children
  that survive a bare kill on the parent and carry on billing, unparented and invisible.
- **`TIMEOUT_HUNG` is a distinct status.** A watchdog kill otherwise reads as `EXIT_137` and looks
  like an ordinary backend crash, which is exactly the kind of thing a tired reader waves through.

Verified both directions: a run writing steadily for 24s survived a 6s idle cap, and a run that
printed a banner then went silent was killed at 10s with zero orphaned child processes.

**If you write your own driver loop instead of using `chain.sh`, put the same watchdog in it** —
that omission is the only reason the $9.94 above was possible.

### If the backend cannot report remaining quota

Common — many backends report only what a run **already cost**, never what is left. Then:

- Leave `QUOTA_PCT_CMD` empty. The pre-flight guard disables itself.
- **A 429 becomes the only true out-of-quota signal.** The chain already treats it as one: discard
  the partial output, back off, retry the same slice.
- Set `COST_CMD` to whatever reports a finished run's cost, so the ledger still fills.
- **Write in the runner's header that there is no pre-flight check.** A reader who assumes a guard
  exists when it does not will queue forty slices into a wall.

Never fake a guard. An unmeasured threshold is worse than an honest absence.

### If the backend is not metered at all

Leave both `QUOTA_PCT_CMD` and `COST_CMD` empty. Slicing still pays for itself in review quality and
speed — you just lose the ledger, and the chain becomes a plain sequential runner. Say that plainly
rather than implying a budget is being managed.

---

## Step 7 — Do not pay to rediscover known bugs

Before the first run, find every prior review of this project — `AUDIT.md`, `*-REVIEW.md`,
`docs/STATUS.md` open todos, closed findings in the git log. Fold the already-fixed items into the
relevant slice briefs as an explicit **"already reported, do not re-report"** list.

Every re-reported finding is budget spent on nothing, twice: once for the model, once for the human
reading it.

---

## Step 8 — Run slice one. Alone. Then recalibrate.

Run exactly one slice. **Never two at once** — parallelism is what caused the failure in
FIELD-NOTES.md, and it does not become safe just because the slices are smaller.

Then read the ledger and answer with the real number:

- What did one slice cost?
- How many fit in one window?
- How many fit in what remains?

**Replace the Step 3 estimate with this measurement in everything you say from here on**, and tell
the user the new number even when it is worse than the guess. If the remaining budget covers fewer
slices than you have, say which tiers get covered and which get left — that is exactly what the
blast-radius ordering was for.

---

## Step 9 — Order the queue, then let it run

Write `queue.txt` (one slice name per line, tier order) and `ORDER.md` (tiers, line counts, and
**why** the order is what it is — see [`references/templates/ORDER.md`](references/templates/ORDER.md)).

Order so that **stopping partway still covers every class of defect that damages a user.** Typical
tiering, adapted to the worst-outcome sentence from Step 4:

1. **Tier 1** — the worst-outcome class itself, plus anything reachable without authentication.
2. **Tier 2** — credentials, and anything that writes to someone else's system.
3. **Tier 3** — concurrency, transactions, schema, silent wrong data.
4. **Tier 4** — UI, performance, tests, documentation drift.

Commit the kit so it survives the session.

To run unattended, launch the chain detached and keep the machine awake:

```bash
nohup caffeinate -i ./docs/<model>-review/chain.sh > docs/<model>-review/nohup.out 2>&1 & disown
```

(`caffeinate` is macOS. On Linux use `systemd-run --user --scope` or `setsid nohup`.)

Confirm it is alive (`pgrep -fl chain.sh`) and hand the user the stop command (`pkill -f chain.sh`)
in the same breath. Never leave an unattended spender running without telling them how to stop it.

---

## Step 10 — Triage before fixing

When reports land:

1. Read every one, including the boring ones.
2. Drop anything already fixed, and anything the model could not verify and you cannot either.
3. **Try to disprove each surviving finding** by reading the code yourself. A second model is a
   generator of hypotheses, not a source of truth — it will confidently report missing checks that
   exist two frames up the call stack.
4. Rank what survives by damage, not by count.
5. **Report to the user before changing code.** They decide what gets fixed.

Then fix in waves matching the tiers, and record what was fixed where the project already records
things (`docs/STATUS.md`, changelog, prodgate evidence).

---

## Step 11 — Three reviewers, then cross-reviewed fixes

**The standing rule: nobody reviews their own work — and "nobody" means the MODEL FAMILY, not the
process.** A Claude subagent reviewing Claude's patch is Claude reviewing Claude. A model that
authored any retained line, test, or piece of evidence for a finding — in ANY earlier round — is
ineligible to review it now, not merely disfavoured. Track authorship per patch across rounds; the
router checks ancestry, not just who touched it last. Claude reviewing what Grok or Sol wrote is real
review — Claude did not write it and is not anchored on the reasoning that produced it. Claude
reviewing Claude is not, and neither is Sol re-reading a file Sol just authored.

This is not a guess about model quality. Measured on Vantage Forms, 2026-08-19: Claude's self-checks
failed the same way three separate times — twice writing a test that codified a bug as correct
behaviour, once marking a real finding "refuted" after answering a narrower question than the one that
mattered. Every time, an outside reviewer caught it. The failure mode is not a higher error rate. It is
that a reviewer who wrote the code checks the question the author framed.

### 11a. Review with all three

Run the review slices through **every selected reviewer** — by default Claude, Grok and Sol — same
prompt, same scope, independently.

If the user chose FEWER: two reviewers still support cross-review, but there is no third opinion to
break a tie, so 11e ends at the first genuine disagreement and escalates. One reviewer cannot satisfy
this step at all — say so plainly rather than pretending a single model's self-check is review. Do not
let them see each other's findings on this pass — agreement is only evidence when it was reached
separately.

Then compare. Three columns per finding: who raised it, what severity, and whether it survived.
Disagreement is the useful signal; a finding only one model saw is not automatically weaker, and one
all three saw is not automatically real.

**Cost: measure it, do not assume it.** The only thing the field notes establish is that SLICING beats
wandering on one backend: three parallel whole-repo GLM lanes burned 21% of a WEEKLY subscription and
returned nothing, while one 588-line GLM slice cost ~1% of a FIVE-HOUR WINDOW. Those are different
denominators and one model. A comparable Kimi slice cost 22% of a window. Nothing has been measured for
Claude, Grok or Sol.

So: calibrate ONE representative slice on EACH selected reviewer (Step 8) before projecting anything,
and report BOTH numbers — unique slices AND total model runs. A 40-slice queue with three reviewers is
120 review runs before a single fix, cross-review, or adversarial round. Steps 3 and 9 size the queue in
slices; the budget guard in Step 6 must be set against runs.

### 11b. Verify each finding against the code before anyone fixes anything

Per Step 10, try to disprove every surviving finding. Prefer an experiment to an argument: build the
artifact and grep it, run the failing case, read the call site.

**But a refuted claim is not a closed concern.** The sharpest lesson from the session that produced
this step: two reviewers called an unfenced block a blocker "because it ships in the free zip". Testing
the built zip proved it does not — the bundler's dead-code elimination removes it. The claim was dead
and the concern was alive: the same block leaked into the generated public SOURCE tree, where there is
no bundler, no dead-code elimination, and every comment survives. The empirical check answered the
narrower question.

So when you refute a finding, say which claim you refuted and which you did not test. "Not in the
artifact" and "not publishable" are different claims with different evidence.

### 11c. Split the fixes by FILE, not by finding

**Only for findings the user approved in Step 10.** Step 10 owns the decision about what gets fixed;
nothing here overrides it. Reviews from all three reviewers are consolidated and triaged together
BEFORE that decision, so no finding reaches a fixer without having passed it.

Fixes are distributed among the reviewers, in parallel. The split must be by **file ownership**, because two agents editing
one file concurrently will clobber each other — and one of them will report success.

Map the write set of every approved fix FIRST. When two findings need the same file, bundle them under
one owner rather than splitting them. When a fix's footprint grows mid-flight beyond its declared
files, the agent stops and asks for reassignment — it does not reach into another owner's file. An
unavoidable overlap is serialized, not parallelized.

Disjoint files are necessary, not sufficient: a change to an interface in one file can break a caller
in another. After all fixers finish, run the full suite once on the settled tree (11f).

Each fix brief states:
- the exact files that agent may modify, and that others are working in the same repo right now
- an explicit list of files it must NOT touch
- no `git commit` / `add` / `checkout` / `stash` — leave everything in the working tree
- **the fixer must observe the failure.** Deliberately break the fix, watch the test or gate fail,
  then restore it. A fix nobody watched fail is not verified, and the fixer must paste both outputs.
  The break must fail for the DEFECT'S reason — a syntax error that turns the suite red proves
  nothing.
- **where the break happens.** In a shared working tree, one agent breaking its file while another
  runs the suite produces a false failure for the second agent. Either give each fixer its own
  worktree, or require the break-restore step to run in a copy of the tree. If neither is possible,
  the fix is marked UNVERIFIED and says so.
- When a defect has no safe deterministic failure to stage — a doc change, a race, a destructive
  migration — the fixer states that, marks the fix UNVERIFIED, and it goes to the user rather than
  being reported as proven.

### 11d. Cross-review every fix

Every fix is reviewed by a model that did not write it. Route by independence: prefer whoever did not
touch that file, and never route a fix back to its author.

Give the reviewer **the claim, not just the diff** — "here is the change, here is what I claim it
proves, here is the evidence I already ran" — so it attacks the claim instead of re-deriving the code.
Name any file that is mid-edit by another agent and tell the reviewer to skip it; a review of a
half-written file is noise.

### 11e. When it is still not right — adversarial rounds, MAXIMUM THREE

If a fix is wrong, contested, or touches something critical, do not just re-fix it. Run an adversarial
exchange: show each model the others' positions and reasoning, and have it argue for or against, citing
the code. Then fix, then re-review.

**A ROUND is one complete argue-then-fix-then-review cycle**, not one model reply. **Hard cap: three.**
Round 4 does not happen.

Give the dispute a stable id at round 1 and carry the counter on that id. A finding that comes back
reworded, re-scoped, or split in two is the SAME dispute and inherits its count — restarting the
counter under a new name is the obvious way this cap gets evaded, including by accident.

If the three converge, record the agreed reasoning, not just the verdict — the next reader needs to
know why the losing option lost.

If they have NOT converged after three rounds, stop and **escalate to the user with the disagreement
stated**. Say exactly what state the working tree is in: a contested patch left applied silently
embodies one side of the argument. Either revert it or mark it clearly as unresolved-and-applied.
Findings that do not depend on the disputed one keep moving; its dependents wait: what each model holds, the strongest argument on each side, and what evidence would settle
it. Never silently pick a side and present it as consensus. An unresolved disagreement reported
honestly is a useful result; a fabricated agreement is not.

Watch for false convergence. Models shown each other's answers tend to agree. Convergence after
independent reasoning is evidence; convergence after one model reads another's confident answer is
often just deference — if a model changes position, its new answer must cite the code, not the
other model.

### 11f. The settled-tree pass

Per-file review leaves a hole: when all three reviewers authored different parts of the change, no one
is eligible to review the COMBINED result, and cross-file integration defects fall straight through the
no-self-review rule.

So, once every edit is settled: run the full suite on the whole tree, and give the complete diff to
whichever reviewer authored the least of it — or, if all three authored substantially, to a fourth
model or the user. Any file that was skipped during 11d for being mid-edit goes on a deferred queue and
is reviewed HERE. Nothing is finished while that queue is non-empty.

---

## Honesty rules

- Never present the slice-count or cost estimate as measured until slice one has run.
- Never report a slice as done when its output contains a quota error — that is a discarded run.
- If a slice fails for a non-quota reason, say so and keep the output; do not silently skip it.
- If the budget runs out partway, state exactly which tiers were covered and which were not. A
  partial review reported as a full one is worse than no review.
- Never report a fix as verified when nobody watched it fail. If the deliberate-break step was
  skipped, say so.
- Never report three-model agreement when the models saw each other's answers first. State whether
  agreement was independent or after exchange.
- Never present a conclusion as consensus when the adversarial rounds ended without one. Report the
  disagreement and hand the decision to the user.
