---
name: sliced-review
version: 2.12.0
description: Review a whole codebase with several models by cutting it into small file-listed slices ordered by blast radius, then triage every finding with three judges, and optionally fix. Use when the user asks to review or audit a whole project or repo with other models, wants a second opinion on a codebase, wants a review split into slices or tiers, has a whole-repo review that died on credits, or wants a check before a launch or handover. Modes (`3`, `5`, `8`, `fast`, `fix …`, `fix fast …`, `fix only`, `report`, `no wrap`) are in the body. Not for a plan before code exists (/grill-me-codex, /codex-review) or a single diff, branch or PR (/code-review).
---

# Sliced Review

> **Model names are short names** (Sol, Grok, Opus, GLM Flash, Composer, DeepSeek Flash, …). The exact version of each lives in ONE place: `~/.claude/skills/_shared/models.md`. Read it before the first dispatch, and write the exact model id from it in every report. Never pick a model by "latest".

Review a whole codebase with another model, without the budget being spent on the model wandering
around the repository.

## The one idea

**The cost is in the wandering, not the thinking.**

A prompt that says *"review this repository"* makes the model glob, grep and read its way across
everything before it reasons about anything. That is where the budget goes, and on a metered plan it
can return literally nothing. A prompt that says *"read exactly these twelve files, never run a
repo-wide grep"* costs a fraction and returns findings.

This holds on a generous plan too — it just shows up as a slower, vaguer review instead of a failed
one. Everything below follows from that single fact.

## Modes — parse the invocation FIRST

The mode changes the model set, whether fixes are applied, and what gets fixed. Read the
invocation before anything else and **state the resolved mode back to the user in one line**
before Step 1, so a misparse is caught before any budget is spent.

| invocation | models | fixes? |
|---|---|---|
| `/sliced-review` (= `3`) | **core three**: Opus, Sol, Grok | no — report only |
| `/sliced-review 5` | core three + DeepSeek Flash + GLM Flash | no — report only |
| `/sliced-review 8` | **main roster**: the five above + MiMo Flash + Qwen Flash + MiniMax Flash | no — report only |
| `/sliced-review fast` | Composer only — a cheap sweep, not a review | no — report only |
| `fix` (= `fix 3`) / `fix 5` / `fix 8` | as above | yes — Step 11c hands the triaged findings to multi-fix (`fix 8` fixes with multi-fix `5`) |
| `fix high` | core three | yes, CRITICAL and HIGH only |
| `fix fast` | 2× Composer review; Sol, Opus, DeepSeek Flash, GLM Flash fix | yes — pipelined per slice (11d) |
| `fix fast 3` / `fix fast 5` | every model reviews AND fixes | yes — pipelined per slice (11d) |
| `fix only` / `fix only 5` / `fix only high` | fixers only, no review | yes — the `open` findings already in `findings.json` (11e) |
| suffix `report` | any | also builds the 12b report without asking |
| suffix `no wrap` | any | skips the closing `/wrap lite` |

Modes compose in any order (`fix 5 high`, `fix fast 3 report no wrap`). Exact model versions and
every provider: [`references/models.md`](references/models.md). A model with several providers runs
on the one `references/pick-provider.py` picks (the subscription whose tokens expire first).

`fast` rates almost everything MEDIUM or LOW, so its severities are not trustworthy for triage
order — say so when reporting a `fast` run, and never let it be the only reviewer before a launch.

### Always finish with `/wrap lite`

**Every mode ends by invoking `/wrap lite`** — unless the invocation contains **`no wrap`**
(`/sliced-review no wrap`, `/sliced-review fix 5 no wrap`). Run it as the last action, after
findings are recorded in Step 12 and after the archive (12c) and any fix commit (11c).

`no wrap` suppresses ONLY the wrap. Everything else about the mode is unchanged.

---

## Create a todo per step and work them in order

One task per step below, worked in order; each step ends on the check it names.

---

## Step 1 — Target, reviewer, scale

Settle three things before touching anything.

**The project.** If the user named one, use it; otherwise the current directory. If `docs/STATUS.md`
or equivalent exists, read it first — it says what is already known broken, which stops you spending
a slice rediscovering it.

**The reviewing models — SET BY THE MODE above**, not chosen here. Each reviews independently
(Step 11a):

| model | effort | provider | invocation |
|---|---|---|---|
| **Opus** | high | **the user's own Claude session** | `Agent(subagent_type: "general-purpose")`, or the `opus` row of `references/templates/lanes.tsv` |
| **Sol** | high | **Codex** | `codex exec --skip-git-repo-check -m gpt-6.2-sol -c model_reasoning_effort="high" -s read-only -o "$T" … < /dev/null` |
| **Astra** (extra lane, no mode yet) | high | **Codex** | same as Sol with `-m gpt-6.2-astra` (smoke-tested OK on Codex CLI 0.170.0, 2026-11-19) |
| **Grok** | high, non-fast | **Cursor or xAI** — `pick-provider.py --model Grok` | `cursor-run.sh --model cursor-grok-4.6-high` (wrapped in `hb.sh`) / `xai-run.sh --grok46` |
| **DeepSeek Flash** | high | **OpenCode Go, Command Code, Cline or Devin** — `pick-provider.py --model "DeepSeek Flash"` | the call table in `references/models.md` |
| **GLM Flash** | max | **OpenCode Go, Command Code, Cline or Devin** — `pick-provider.py --model "GLM Flash"` | the call table in `references/models.md` |
| **MiMo Flash** (`8`) | high | **OpenCode Go, Command Code or Cline** — `pick-provider.py --model "MiMo Flash"` | the call table in `references/models.md` |
| **Qwen Flash** (`8`) | high | **OpenCode Go or Command Code** — `pick-provider.py --model "Qwen Flash"` | the call table in `references/models.md` |
| **MiniMax Flash** (`8`) | default | **OpenCode Go** | `oc-run.sh --model opencode-go/minimax-m3.1-flash` |
| **Composer** (`fast` only) | default | **Cursor** | `cursor-run.sh --model composer-2.5` |
| **Gemini Hydrogen / Carbon / Argon / Flash** (extra lanes, no mode yet) | high | **Antigravity** (Flash also Cursor) | `agy-run.sh --hydrogen` / `--carbon` / `--argon` / `--flash` |

Never route Sol or Opus through Cursor. Grok on Cursor and Composer share ONE Cursor pool, so they
never run at once. **Opus is not independent on anything Claude built**: weight its agreement below
Sol's or Grok's there.

**Provider notes: read `references/runners.md` → "Provider notes" before the first dispatch.** It holds the
Swift rule (Sol builds Swift through OpenCode, not Codex), Luna, Pi as the main OpenCode driver,
the free OpenCode and Cline arms, xAI and Devin, and which routes run the SAME model — two routes
of one model are never a fix and its cross-check, nor two reviewers in one scorecard.

A model that is not in `models.md` can still be wired: `references/runners.md` → "Wiring a backend
that is not listed" has the four questions to answer. State in one line whether each selected model
can report remaining quota; it changes Steps 6 and 8.

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
- Skip `lane.sh` and `queue.txt` entirely. Keep `_context.md` and the slice briefs — those are what
  make the review good, not the machinery.
- Still keep a ledger line per run if the backend is metered.

### Medium — ~5,000 to ~20,000 lines

- **6–15 slices**.
- Build the kit and run it with `lane.sh` (Step 6).
- Usually finishes in one sitting.

### Large — over ~20,000 lines

- **20–45 slices**. The full kit: context, briefs, queue, lanes, ledger, ORDER.md.
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

### 4a. Write the trust map — `_trustmap.md`, 60 lines at most (added v2.4)

Slices see files in groups, so a chain that crosses two slices is invisible to every lane. One short
shared map, written once and read by every lane, closes that gap.

Read the entry files, routers and auth code (not the whole repo) and write four short lists:

1. **Entry points** — every way input reaches the code: routes, every entry script the platform
   serves (for WordPress: `index.php`, `admin-ajax.php`, `admin-post.php`, `xmlrpc.php`,
   `wp-login.php`, `wp-cron.php`, REST batch), CLI, cron and queues, webhooks, the installer, and the
   **update channel** (how a new version reaches installs).
2. **Principals** — who can send each input, lowest trust first: anonymous, a logged-in low role,
   an app password or API token, a cookie admin, another plugin or service on the same host, CI.
3. **Controls** — each check that is meant to stop a lower principal, with file:line, and every
   path that is **exempt** from it (allow-lists, "link routes", health checks, internal calls).
4. **Assets** — what the worst outcome touches: the data, the switch, the key, the money.

Then add one line per known **auth-method swap**: a way one principal turns into another (app
password → create a user → cookie login; API token → mint a session; webhook → admin action).

Paste `_trustmap.md` into the shared context under `TRUST MAP`. Every slice brief may cite it, and
the chain lane (Step 5) is built on it. Keep it to facts with file:line — no findings in the map.

---

## Step 5 — Write the shared context and the slice briefs

Create `docs/<model>-review/` in the project (e.g. `docs/glm-review/`, `docs/sol-review/`).

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

### Two cross-cutting slices every run adds (v2.4)

These read across the slice lines on purpose. They are small, and they run on the same lanes as the
rest.

- **`x01-chains`** — reads `_trustmap.md` plus the entry and auth files it cites (cap: 8 files).
  Questions: for each principal, list every path in the map that lets it reach a control's
  protected asset **without** passing that control — through an exempt route, an auth-method swap,
  a sibling plugin or service, an entry script other than the main one, or an internal call that
  skips the check. Each answer must be a chain of steps with file:line per step.
  **Also re-check every item the slice briefs mark *accepted* or "already reported" against the
  map.** Accepted is not the same as safe: one accepted line once hid a run's only critical.
- **`x02-release`** — the supply chain and release path. Read: the plugin or package header and
  manifest, the release and build scripts, CI workflows, lockfiles and dependency pins, install and
  update code. Questions: can anyone but the owner push an update to installs (missing `Update URI`,
  a registry name nobody owns, an unpinned download)? Do CI or release steps expose a secret to a
  fork or a pull request? Does the shipped package include dev files, tests or keys? Are dependency
  floors and pins what the code needs?
  **Tool pre-pass first (v2.7):** run `references/templates/prepass.sh <repo> <kit>/prepass.md`
  (gitleaks with values redacted, osv-scanner) and paste its output into this brief. A tool that
  is not installed shows as NOT RUN; say so in the report.

On a repo with no security boundary and no release channel (a private script, say), skip them and
say so in `ORDER.md`.

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

A **small** project: run the briefs by hand, one model and one slice at a time, and go to Step 7.

Otherwise the kit lives on the laptop (all review work runs there through `ssh laptop`) under
`~/work/sr-kits/`, and [`references/templates/lane.sh`](references/templates/lane.sh) runs it — one
`lane.sh` per model, all at once, sharing the queue through an atomic claim file:

- `<app>/WORKDIR` (the repo path, at the commit under review), `<app>/_context.md`,
  `<app>/slices/`, `<app>/queue.txt`.
- `lanes.tsv` — one line per lane: lane, provider (the codexbar key), model id, command. Start from
  [`references/templates/lanes.tsv`](references/templates/lanes.tsv) (the main roster on each
  provider) and keep the rows `pick-provider.py` picks. `slots.conf` caps lanes per provider.
- A report counts only when it ends with `TOTAL FINDINGS: <n>` (the `_context.md` template asks for
  it). Every run writes a ledger row: time, lane, provider, model, slice, status, seconds, bytes,
  tokens. `usage.py` fills tokens and the API-equivalent price for every route, flat plans and free
  ones too; a price it cannot find is `unknown`, never invented (add the id to `prices.json`).
  **Missing price → OpenRouter's public list** (no key, no spend), and `usage.py` saves it to
  `prices.json` with the date (`"saved"`, `"from"`), so that model's price stays fixed for later
  runs. The save lands on the machine that ran `usage.py` (usually the laptop): copy new rows back
  into the Mac's `prices.json` before the next sync to the laptop, or the sync overwrites them.
- **Watchdog:** idle cap 900 s (2,400 s for Codex, Claude and Command Code), hard cap 3,000 s; it
  kills the whole process group, because these backends leave billing children behind. A hang
  never errors, so the watchdog is the only thing that stops one. Cursor prints nothing until it
  ends: its lanes run inside `hb.sh`, which prints a dot a minute (the template does this).
- **Quota:** a QUOTA status waits 15 minutes and retries, up to 8 times, then stops that lane.
- **Stop and drain** with files, never `pkill -f`: `touch ~/work/sr-kits/STOP` (all lanes),
  `STOP.<provider>` or `STOP.lane.<lane>`; `DRAIN.lane.<lane>` or `DRAIN.<provider>` lets the current
  slice finish and starts no new one.
- One model on one box can still use `run-slice.sh` + `chain.sh` + `runner.env` from the same folder
  (one slice at a time, same watchdog idea).

Before starting anything in the background, read `references/runners.md` → "Orchestration gotchas",
"Gotchas that keep biting" and "Linux laptop".

---

## Step 7 — Do not pay to rediscover known bugs

Before the first run, find every prior review of this project — `AUDIT.md`, `*-REVIEW.md`,
`docs/STATUS.md` open todos, closed findings in the git log. Fold the already-fixed items into the
relevant slice briefs as an explicit **"already reported, do not re-report"** list.

**Fixed items only.** Never put an *accepted*, *wontfix* or "by design" item in that list
as a plain "do not report" — say "accepted for reason X; report it if any path makes it worse".
`x01-chains` re-checks every one of them (Step 5).

**Neutral wording for accepted items.** State the accepted reason as a plain fact with its
condition ("accepted 10-12: needs the admin role; reason X"). Never write "assumed harmless",
"safe because", "not exploitable" or similar in a brief or a judge prompt. That wording anchors the
reviewers and the severity judge low.

Every re-reported finding is budget spent on nothing, twice: once for the model, once for the human
reading it.

---

## Step 8 — Run slice one on each lane. Then recalibrate.

Before the full queue, run ONE slice on each lane: `ONLY=<slice> ./lane.sh <app> <lane>`. Whole-repo
lanes in parallel once emptied a weekly subscription for zero findings; one slice per lane first is
how that is caught cheaply.

Then read the ledger and answer with real numbers, per lane: what did one slice cost in time and
tokens, how many fit in the window that is left (`pick-provider.py` prints the windows), and how
many runs the whole queue needs (slices × lanes).

**Replace the Step 3 estimate with this measurement from here on**, and tell the user the new number
even when it is worse than the guess. If the budget covers fewer slices than you have, say which
tiers get covered and which get left — that is what the blast-radius order is for.

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

Record each slice's file hashes before the first lane starts (v2.7), so a finding on a file that
changed later is caught as STALE:

```bash
for sl in $(cat <kit>/queue.txt); do python3 ~/.claude/skills/sliced-review/references/templates/slice-guard.py record <kit> "$sl"; done
```

Commit the kit so it survives the session.

Start one lane per model on the laptop, detached, and say how to stop them in the same breath:

```bash
ssh laptop 'cd ~/work/sr-kits && mkdir -p <app>/logs && for l in <lane> <lane> <lane>; do
  setsid nohup ./lane.sh <app> "$l" > <app>/logs/"$l".log 2>&1 < /dev/null & done'
```

Stop: `ssh laptop 'touch ~/work/sr-kits/STOP'` (or a `STOP.lane.<lane>` / `DRAIN.lane.<lane>` file).
Never leave an unattended spender running without telling the user how to stop it.

### The live report — on for every run (v2.6)

Start it as soon as the first lane starts, in the background on the Mac (codexbar and the `claude`
CLI live there). The tools are in [`references/live-report/`](references/live-report/); copy that
folder to the kits host first (`scp -r` to the same path), because `collect.py` runs there.

```bash
SR_HOST=laptop SR_KITS=~/work/sr-kits SR_APPS=<app>[,<app>] \
  ~/.claude/skills/sliced-review/references/live-report/monitor.sh <review-dir>/live "<Project name>"
```

Every 4 minutes it collects every lane and judge, reads the subscription windows, has **Haiku 5.5**
check the run (`haiku-check.py`: a plain-words summary, alerts, one note per lane), and writes
`<review-dir>/live/report.html`. The page shows the project, the slices, each model with its
provider, whether it is active and on which project and slice, time, tokens (in, cached, out),
API-equivalent cost, findings per severity, the triage judges, and every subscription's window.

- Publish `report.html` as an Artifact after the first round, and republish the same path at each
  check-in. `PUBLISH_CMD` can push it somewhere else after every round.
- Act on the monitor's alerts: a stuck slice, a lane that keeps failing, a subscription at 90%.
- It stops by itself after two rounds that find the run finished; `touch <review-dir>/live/STOP`
  stops it early.

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

**The triage panel — three judges, every time (v2.6).** Each slice's triage runs on at least three
models, each judging the same reports on its own. A finding is CONFIRMED when two judges confirm it
with file:line; a split goes to the final severity pass with each judge's reason attached. Pick the
panel:
- **Default panel:** Opus, Sol and Grok.
- **Cheaper panel:** two of DeepSeek Flash, Qwen Flash, MiMo Flash or Luna (xhigh), plus at least one
  of Opus, Sol or Grok.
  - With Luna on the panel, the main judge is Opus or Grok (Luna and Sol share the Codex pool).
  - Sol joins a cheaper panel only when Luna is off it, or when Opus and Grok are both out of quota.
- A judge with several providers runs on the one `references/pick-provider.py` picks.
- Write each judge's model id and provider in the triage ledger and the scorecard.
- Each judge runs on its own lane name, with no `alias.tsv` entry. Judges that share an alias
  share one claim per slice, so only the first judges it (seen 2026-10-25: Sol said "queue done").

**Before the judges read anything (v2.7),** run the guard on every lane report:
`slice-guard.py check <kit> <slice> <report.md>`. It costs no tokens.
- Drop a finding when every file:line it cites is `missing-file` or `bad-line` (a made-up file or
  a line past the end of the file). Count the drops per lane in the scorecard.
- A finding on a `stale` file (changed since the hashes were recorded, e.g. by a pipelined fix) is
  STALE: the judges re-check it against the current code instead of trusting it.
- An `out-of-slice` finding is kept: route it to `x01-chains`, or to the triage of the slice that
  owns the file. Log it per lane in the scorecard: the lane read past its file list.
- `quote_not_near` is a hint for the judges, not a drop.
- Each lane's LEADS section enters triage as NEEDS-VALIDATION rows (merged by the rule below).

**Every judge prompt (v2.7) carries:**
- the untrusted-repo block from `references/templates/_context.md`, word for word;
- **step 0, restate the claim** in the judge's own words: source → sink → the missing control,
  with file:line for each. A claim the judge cannot restate this way is FALSE-POSITIVE or
  NEEDS-VALIDATION, never CONFIRMED;
- **rationalizations to reject** — none of these is evidence:

  | rationalization | what the judge does instead |
  |---|---|
  | "the pattern looks dangerous, so it is a bug" | trace input to sink in this code |
  | "similar code was bad elsewhere" | judge this call path only |
  | "this is clearly critical" | grade by the severity anchors |
  | "skip the full check to save time" | finish the trace, or mark NEEDS-VALIDATION |

**Verdicts.** Use exactly three:
- **CONFIRMED** — the code proves it; quote file:line for each step.
- **NEEDS-VALIDATION** — it may be real, but one fact is missing. Name **the exact missing fact**
  ("does real Novamira's admin-access handler return a login URL to an app-password caller?") and
  **the safest way to settle it** (a test, a read of a named file outside the repo, a staging
  request). No severity until it is settled — **except** when the missing fact is a documented,
  supported setting (see the final severity pass).
- **FALSE-POSITIVE** — the code disproves it; say why with file:line.

**Severity anchors** — grade by these, never by the lane's label:

| severity | test |
|---|---|
| critical | a low-trust or anonymous principal **fully defeats** the main control or reaches the worst outcome from Step 4, with no unusual precondition |
| high | fully defeats an explicit control, with a realistic precondition (a valid low-privilege login, a common server setup) |
| medium | partly defeats a control, needs an unusual precondition, or breaks availability of the control (lockout, fail-closed for real users) |
| low | hardening, test and fixture gaps, docs/code drift, small correctness bugs with no crossed boundary |
| info | true but no consequence |

The high/medium line is the one that drifts: **does the result fully defeat an explicit control?**
Yes → high or above. Only partly, or only with an unusual precondition → medium.

**A security claim must name its boundary.** For any finding about access, auth, keys, tenants or
money, the triage row states: the lower-trust **principal**, the **input** it sends, the **control**
meant to stop it, the **boundary** crossed, the **asset** reached, and the concrete **result**. If
a lane's claim cannot fill those six, it is not a security finding: re-file it as low (hardening) or
drop it. Drop on sight:
- checklist items with no path ("no rate limit", "consider CSP") where nothing crosses a boundary;
- defense-in-depth only, where the principal already owns the asset (a stolen admin password that
  "could" do admin things) — unless the code **claims** that defence, then it is a docs/code
  mismatch, low;
- a scanner-style pattern match the lane did not trace to a reachable entry point;
- severity argued from a hypothetical deployment the trust map does not show.

Test gaps, docs drift and correctness bugs keep their normal rows — this filter is for security
claims only. Breadth is what the sliced review is for; do not throw it away.

**Merge duplicate leads across slices.** After each slice is judged, group every
NEEDS-VALIDATION row by root cause (same missing fact, same code path). Keep ONE row per lead, list
every slice and lane that raised it, and keep the sharpest "missing fact + safest check" text.

**One final severity pass across slices.** Per-slice judges grade the same chain differently.
After all slices are
judged, ONE judge (the strongest lane available, never a lane that reported the finding alone)
reads every CONFIRMED row that shares a root cause or chain and sets one severity by the anchors.
Tie-break: **if the product's README or docs claim protection against this principal, grade by the
anchors — not by the defense-in-depth drop rule.** A precondition that is a documented, supported
setting (a config constant the README tells people to set) is realistic, not unusual. Record each
changed severity with the old value in the scorecard.

Rules for this pass:
- **Grade documented-setting leads too.** Also read every merged NEEDS-VALIDATION lead whose
  missing fact is only "is this documented, supported setting turned on?" (a config constant, an
  option the README or docs describe). Grade it as if the setting is on, and keep the lead label
  with that condition written next to the severity ("HIGH if `TRUST_PROXY_HEADER` is set"). Leads
  whose missing fact is anything else stay ungraded.
- **Worst outcome first, then preconditions.** For each security group, first ask: with the
  precondition met, does the result **fully defeat** the control or reach the Step 4 worst outcome?
  If yes, **high is the floor**: grade it critical when the precondition is not unusual,
  and high when the precondition is truly unusual by the anchors. A full defeat is **never** medium
  or low; the one-step drop for an unusual precondition is critical -> high, never high -> medium.
  Never lower a grade just because "it needs X" when X is a normal or documented state. Put this floor in the severity
  judge prompt word for word.
- **Same-instant admin race.** The floor drops only when the precondition needs two or
  more trusted actions at the same instant (a race between admins or operators). Then grade by the
  anchors, usually medium. Everything else keeps the floor: one normal admin action, a plugin or
  cleanup tool, a load-order mistake the docs warn about, or any state the site can reach by itself.
  The judge writes who meets the precondition next to the grade. Put this rule in the
  severity judge prompt word for word too.

**Coverage pass.** After triage, list every entry point and control in `_trustmap.md` and
mark which slice or lane covered it (a finding, or a lane that says it checked it clean). Any entry
or control **nobody** covered goes into one small gap slice (`x03-gaps`, max 6 files) on the
cheapest strong lane. Record the coverage table in the scorecard file.

**In `fix` modes** The user has already authorised applying what this triage approves, so step 5
becomes: report the triage, then proceed into 11c without waiting. Report it anyway — the user can
still stop it — and keep 11c's stop cases out of the automatic path.

Then fix in waves matching the tiers, and record what was fixed where the project already records
things (`docs/STATUS.md`, changelog, prodgate evidence) — **and in `docs/reviews/findings.json`
(Step 12), which is the one place the board and Mission Control read.**

### The model scorecard — every multi-model run ends Step 10 with one

Triage produces the one thing raw reports cannot: which claims were TRUE. Use it. Before moving to
fixes, write **`docs/reviews/scorecard-<YYYY-MM-DD>.md`** from `templates/scorecard.md` and put the
table in the report to the user. One row per reviewing model:

| column | meaning |
|---|---|
| reported | findings the model wrote, after de-duplicating within its own reports |
| verified / refuted | survived Step 10 (and 11b if it ran) / disproved against the code |
| precision | verified ÷ reported |
| crit · high · med · low | **verified** findings by severity — never the model's own labels on unverified claims |
| unique | verified findings no other model reported |
| missed crit/high | verified critical or high findings that other models reported and this one did not |
| score | Σ weights over verified findings: critical 8, high 4, medium 2, low 1, info 0 |
| total time · avg / slice · slowest slice | from `ledger.tsv`: the sum of that model's slice wall clocks, the mean, and its longest single slice with the slice id. Per-model queue time, not the run's wall clock — lanes run in parallel |
| cost | from the ledger, so the score has a price next to it (what the backend billed; blank on a flat plan) |
| tokens · api_usd | from the ledger's token columns: tokens in / cached / out, and their API-equivalent price — filled for EVERY model, flat plan and free routes too, so the price comparison is like for like. `unknown` = no price found |

**Rank by score.** Ties break by unique, then precision. Time never enters the rank — but it sits
in the same row so a model that scored second in a third of the time is visible as the bargain it
is. Under the table, one sentence per model on
why it ranks where it does, then a line for anything **every** model missed that triage found by
hand or from the live database — that line is the honest ceiling of the whole stack.

Rules that keep the table from lying:

- **Grade on verified findings only.** A model with 20 claims and 15 refutations ranks below one with
  5 claims all true. Raw count rewards wandering and confident noise.
- **Severity is the triager's, not the model's.** A model calling a nit "critical" does not make it
  one; re-grade before counting.
- **Same defect from two models is one finding**, credited to both. It counts toward neither's
  `unique`.
- **A lane that died or was killed gets a row with its coverage stated**, not a zero that reads as
  "found nothing".
- In `fast` mode (one reviewer) write the table anyway — one row, no rank — so the run is
  comparable to the next.

The scorecard is what decides which models the next run buys. Over time it is also the evidence
behind the roster in Step 1, so keep the formula fixed; a run graded on a different formula cannot be
compared to this one.

---

## Step 11 — Independent reviewers, then fixes through multi-fix

**Nobody reviews their own work — and "nobody" means the model family, not the process.** A Claude
subagent reviewing Claude's patch is Claude reviewing Claude. A model that wrote any kept line, test
or piece of evidence for a finding, in any earlier round, may not review it. Claude reviewing what
Grok or Sol wrote is real review. Self-checks fail by answering the question the author framed: an
outside reviewer caught that each time it was measured.

### 11a. Review with every model in the mode's set

Run the slices through **every reviewer the mode selects** — same prompt, same scope, independently.
No reviewer sees another's findings on this pass: agreement is evidence only when it was reached
separately. `fast` is ONE reviewer and therefore not review; say so in the report. Two reviewers
have no tie-breaker, so a real disagreement goes to the user at once.

Then compare: who raised each finding, at what severity, and whether it survived. A finding only one
model saw is not weaker for it, and one all of them saw is not true for it.

Report both numbers when you size the work: unique slices AND total runs. 40 slices × 3 reviewers =
120 review runs before a single fix. Step 8 measured the cost per run; use it.

### 11b. A refuted claim is not a closed concern

When you disprove a finding, say which claim you refuted and which you did not test. "Not in the
built artifact" and "not publishable" are different claims: the code a bundler strips from the zip
can still ship in a public source tree.

### 11c. `fix` modes — triage here, fix with multi-fix

Report-only modes end at Step 10. In `fix`, `fix 5` and `fix high`, the user has already said yes to
fixing what triage approves, so after reporting the triage, run the multi-fix procedure
(`~/.claude/skills/multi-model-fix/SKILL.md`, Steps 3–9) with `docs/reviews/findings.json` as the
ledger:

- Same model set as this mode; `fix 5` uses the main-roster ring there.
- `fix high` drops everything below HIGH **before** any fixer is briefed; the rest stays `open`.
- Its briefs carry the untrusted-repo rule, a regression test per fix and a variant hunt.
- Split by file, rotated cross-check (Opus is checked by a non-Claude model), at most three
  adversarial rounds, settled-tree pass, ONE commit. The session model's approval is an integration
  gate, not a third review — say so.
- **Stop and ask** when a fix would delete or migrate data, change a public interface, touch
  credentials or billing, or when the models disagree that the defect is real. The rest keeps moving.

### 11d. `fix fast` modes — pipelined

A slice's fixes start the moment its triage lands, while later slices are still in review. Same
triage, rotation, settled-tree pass and single commit as 11c; only the scheduling changes.

- **`fix fast`:** two Composer lanes review. Sol, Opus, DeepSeek Flash and GLM Flash fix in turn; Grok
  joins only when Composer is done (they share the Cursor pool).
- **`fix fast 3` / `fix fast 5`:** each model runs one reviewer and one fixer at once. A model may fix a
  slice it reviewed; it never checks its own fix.
- **Overlapping write sets:** slices share files. Before dispatching a fixer, compare its files with
  every fixer in flight; serialize behind the owner, or give each its own worktree. A finding on a
  file a fix already changed shows as STALE in `slice-guard.py check`; re-check it on the new code.
- **Cursor concurrency** rises (`fix fast`: 2 Composer; `fix fast 3`: 2 Grok; `fix fast 5`: up to
  2 Grok on Cursor). Failures from Cursor mean the pool is empty: drop to one Cursor lane and go on.

### 11e. `fix only` — fix a review that already ran

Skips Steps 1–9 and 11a. Input: every `open` entry in `docs/reviews/findings.json`, plus the slice
reports its review folder holds (`docs/reviews/<date>-<mode>/lanes/`, Step 12c). No recorded review
→ stop and say *"No recorded review to fix — run /sliced-review first."* Never review again to fix.

1. State the inventory in the one-line mode statement (findings by severity, reviews, commits since).
2. Re-triage against the CURRENT tree: still real → queue it; already gone → `fixed` with the commit
   (`git log -S`) or `false-positive` with a note; moved → fix the `file` field, then decide.
3. Then 11c. The scorecard is not rebuilt (no review ran); re-run the 12b report if asked.

---

## Step 12 — Record the findings where the dashboards read them

A review that lives only in `out/*.md` is invisible a week later. Every review ends by writing
**`docs/reviews/findings.json`** in the project root — the machine-readable record that
`prodgate aggregate` collects and that playbook.nottod.com and mc.nottod.com/reviews render as
"what is next on this project". Copy `templates/findings.json` if the file does not exist.

Spec: `~/Desktop/Claude/prodgate/CONTRACT.md` → "Review findings"; schema
`~/Desktop/Claude/prodgate/schema/findings.schema.json`. The rules that matter:

1. **One `reviews[]` record per run**: `id` = `<short-model>-<YYYY-MM-DD>`, `model` = the real
   model id from `runner.env` (`gpt-6.2-sol`, `grok-4.5`, `glm-5.3`, …), `kind: "sliced-review"`,
   `dir` = this review's folder, `slices` = number of slice outputs.
2. **One `findings[]` entry per DISTINCT defect** that survived Step 10. The same defect from two
   models is one entry (say "also found by …" in `note`). Skip style nits with no file. Fill
   `file` as `path:LINE` whenever the report names one. `severity`: critical | high | medium |
   low | info. `found_at` = the review date.
3. **`verified: true` only for what a human or an executed test confirmed.** A model's claim is
   `false` until then. The dashboards show the two counts apart, so lying here shows.
4. **Status follows the work**: `open` until a commit closes it; `fixed` needs `fixed_at` and
   `fix_commit`; `wontfix` / `false-positive` need a `note` saying why. **Never delete an entry.**
5. **Never put a finding in `.prodgate.yml`.** If a finding is an instance of a tip, set `tip`
   (`r39`, `owasp-a01`, …) and `tier`; the tip's own entry is where the gate decision lives.
6. Validate before committing:
   `node ~/Desktop/Claude/prodgate/bin/prodgate validate-findings --project <project root>`
   must exit 0. Commit the file with the review's other docs, then run `/prodgate-refresh` once.

`/wrap` re-reads the entries a session touched, the same way it re-reads `.prodgate.yml`; a
session that fixes a finding and leaves the file alone leaves the board reporting an open bug.

### 12b. The report — `report` suffix, or ask

`findings.json` is for machines and the scorecard is one table. When a person needs to READ the
review — the user a week later, a client, a teammate who was not in the session — build the report:

```bash
python3 <skill dir>/templates/build-report.py --project <project root>
```

It writes **`docs/reviews/report-<date>.md`** and **`docs/reviews/report-<date>.html`** from the
same three records — `findings.json`, `scorecard-<date>.md`, and each lane's `ledger.tsv` — so the
two never drift. The HTML is one self-contained file (no scripts, no external assets, prints
cleanly, light and dark) that opens anywhere. Both carry: the counts, the scorecard with its ranking
prose, a lanes table with total time / avg per slice / slowest slice / slice status per model, and
every finding grouped by severity with file, status, who found it, verified or not.

**When it runs:**

- If the invocation carried the **`report`** suffix (`/sliced-review 5 report`,
  `/sliced-review fix fast 3 report`), build it here without asking, and open the HTML for the user.
- Otherwise, **ask once**, after `findings.json` is written and before `/wrap lite`: *"Build the
  Markdown + HTML report? (y/n)"*. Do not build it unasked — it is a deliverable, and an unwanted
  file in `docs/reviews/` is noise the next reader has to explain.

The generator decides nothing. It renders what triage recorded: a wrong severity or a missing
`verified` in `findings.json` shows up wrong in the report, and the fix is the JSON, never the
HTML. Commit the two report files with the review's other docs. Re-run after fixes land so the
status column matches the commits.

### 12c. Save the whole review — every run, every mode

A review must still be readable months later, with what each model found, how long it took and
what it cost. After `findings.json` and the scorecard are written, archive the run into the project:

```bash
ssh laptop 'python3 ~/.claude/skills/sliced-review/references/live-report/archive.py \
  --app <app> --mode "<mode as invoked>" [--live <dir with the monitor status.json>]'
```

It writes `docs/reviews/<date>-<mode>/` in the reviewed repo (the kit's `WORKDIR`):

- `REVIEW.md` — the document: per model the provider, slices, total / average / slowest time,
  tokens in / cached / out, API-equivalent cost, findings by severity, failures and guard counts;
  the triage judges and every confirmed finding; and a map of the folder.
- `report.html` + `snapshot.json` — the live-report page, frozen at the end.
- `inputs/` (brief, trust map, slices, queue, pre-pass, hashes, lane commands, `models.md` as it
  was), `lanes/` (every slice report and ledger), `triage/` (every judge's verdicts), `guard/`.

It also adds one line to `docs/reviews/INDEX.md`. Commit the folder with `findings.json` and the
scorecard. gitleaks runs before any push, as always. In `fix` modes, archive before the fix commit
so the review and the fix are separate commits.

---

## Honesty rules

- Never present a slice-count or cost estimate as measured until Step 8 has run.
- A slice whose output holds a quota error is a discarded run, never a done slice.
- A slice that failed for another reason is reported as failed, with its output kept.
- If the budget runs out partway, say exactly which tiers were covered and which were not.
- `verified: true` means a person or a test saw it; `fixed` means a commit sha. Never on a model's
  say-so.
- Rank models on verified findings at the triager's severity, never on raw counts or their own labels.

## Keep the prompt cache warm (added 2026-10-08)

A Claude subagent loses its prompt cache after 5 minutes without a request, and then pays for its
whole context again (about $0.75 each time). So: no tool call of a subagent waits longer than 230
seconds. Start every long run (builder, reviewer, `codex exec`, a long test suite) in the
background and wait in short steps, with the scripts and the rule in
`~/.claude/skills/sliced-review/references/keep-warm.md`. Put this rule in the brief of every
subagent that will wait for a run.
