# sliced-review

**Version 2.3.1** — see [`CHANGELOG.md`](CHANGELOG.md). Your installed version is the `version:` line in `SKILL.md`.

A Claude Code skill that reviews a whole codebase with a second model **without the budget being spent on the model wandering around the repository**.

It splits the codebase into scoped slices with explicit file lists, orders them into tiers by blast radius, and drives them one at a time with a cost ledger, an activity-aware watchdog, and an optional quota guard. Works with any headless backend — a metered subscription, a pay-as-you-go API, a local model, or a Claude subagent.

> **The one idea:** the cost is in the wandering, not the thinking. A prompt that says *"review this repository"* makes the model glob, grep and read its way across everything before it reasons about anything. A prompt that says *"read exactly these twelve files, never run a repo-wide grep"* costs a fraction and returns findings.

Read [`FIELD-NOTES.md`](FIELD-NOTES.md) first — it is the measured evidence behind every rule in the skill (three parallel whole-repo lanes that burned 21% of a weekly plan for zero findings; a 20k-line codebase later reviewed for 4% of the same plan; a backend that hung silently for 19 hours).

## What's in the box

| Path | What it is |
|---|---|
| [`SKILL.md`](SKILL.md) | The skill itself — invocation modes, then 12 steps from measuring the codebase to recording the findings |
| [`CHANGELOG.md`](CHANGELOG.md) | What changed in each version |
| [`FIELD-NOTES.md`](FIELD-NOTES.md) | Measured results from real runs. Why each rule exists |
| [`references/runners.md`](references/runners.md) | How to wire a review backend: the four questions, plus worked examples |
| [`references/templates/_context.md`](references/templates/_context.md) | Shared context every slice prompt starts with |
| [`references/templates/run-slice.sh`](references/templates/run-slice.sh) | Runs ONE slice: quota guard, idle + hard-cap watchdog, process-group kill, ledger line |
| [`references/templates/chain.sh`](references/templates/chain.sh) | Works the queue unattended; retries on 429, never records a quota error as a report |
| [`references/templates/ORDER.md`](references/templates/ORDER.md) | Tier-order template: what is still covered if the budget dies after tier 2 |
| [`templates/findings.json`](templates/findings.json) | Shape of the `docs/reviews/findings.json` record every review ends by writing (Step 12) |
| [`templates/build-report.py`](templates/build-report.py) | Renders the Markdown + self-contained HTML review report from `findings.json`, the scorecard and the ledgers (Step 12b; `report` suffix or asked once) |
| [`templates/scorecard.md`](templates/scorecard.md) | Per-model scorecard every multi-model run ends Step 10 with: verified findings by severity, precision, unique finds, rank |

## Install

```bash
git clone https://github.com/Mariomarquezt/sliced-review ~/.claude/skills/sliced-review
```

Then in Claude Code: "review the whole codebase with GLM" / "audit this project with a second model" / `/sliced-review`.

## Modes

| invocation | reviewers | applies fixes? |
|---|---|---|
| `/sliced-review` or `/sliced-review 3` | core three: GPT-5.6 Sol (xhigh), Grok 4.6 (high), Opus 5 (high) | no |
| `/sliced-review 5` | core three + GLM 5.3 Flash + Composer 2.5 | no |
| `/sliced-review fast` | Composer 2.5 alone | no |
| `/sliced-review fix` / `fix 3` / `fix 5` / `fix high` | as above | yes — triage, fix, cross-check with a different model, commit |
| `/sliced-review fix fast` / `fix fast 3` / `fix fast 5` | as above | yes, pipelined per slice |
| `/sliced-review fix only` / `fix only 5` / `fix only high` | fixers only, **no new review** | yes — re-verifies the open findings a previous run recorded in `findings.json`, then fixes them |

Append `no wrap` to skip the closing wrap-up. Append `report` to build the Markdown + HTML review report without being asked; otherwise the skill asks once at the end. The models are the author's measured stack; swap in whatever your `runner.env` can reach.

## Wiring your own backend

The backend lives in **one file**, `runner.env`, generated per project in Step 6. The wrapper scripts named in `references/runners.md` (`~/.hermes/glm/glm-run.sh`, `~/.hermes/kimi/kimi-run.sh`, `~/.hermes/cmd/cmd-run.sh`) are the author's local one-shot launchers and are **not included** — they are examples of the shape, not dependencies. Any command that takes a prompt and prints a report works:

```bash
RUNNER_CMD='codex exec -m gpt-5.6-sol "$(cat {PROMPT_FILE})" < /dev/null'
QUOTA_PCT_CMD=''   # leave empty if the backend cannot report remaining quota
COST_CMD=''
```

`references/runners.md` lists the four questions to answer for any backend.

## Honesty rules (from the skill)

- Never present a cost estimate as measured until slice one has run.
- Never report a slice as done when its output contains a quota error.
- If the budget runs out partway, state exactly which tiers were covered.
- Never report a fix as verified when nobody watched it fail.
- Never report multi-model agreement when the models saw each other's answers first.

## License

MIT — see [`LICENSE`](LICENSE).
