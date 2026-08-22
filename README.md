# sliced-review

A Claude Code skill that reviews a whole codebase with a second model **without the budget being spent on the model wandering around the repository**.

It splits the codebase into scoped slices with explicit file lists, orders them into tiers by blast radius, and drives them one at a time with a cost ledger, an activity-aware watchdog, and an optional quota guard. Works with any headless backend — a metered subscription, a pay-as-you-go API, a local model, or a Claude subagent.

> **The one idea:** the cost is in the wandering, not the thinking. A prompt that says *"review this repository"* makes the model glob, grep and read its way across everything before it reasons about anything. A prompt that says *"read exactly these twelve files, never run a repo-wide grep"* costs a fraction and returns findings.

Read [`FIELD-NOTES.md`](FIELD-NOTES.md) first — it is the measured evidence behind every rule in the skill (three parallel whole-repo lanes that burned 21% of a weekly plan for zero findings; a 20k-line codebase later reviewed for 4% of the same plan; a backend that hung silently for 19 hours).

## What's in the box

| Path | What it is |
|---|---|
| [`SKILL.md`](SKILL.md) | The skill itself — 11 steps from measuring the codebase to cross-reviewed fixes |
| [`FIELD-NOTES.md`](FIELD-NOTES.md) | Measured results from real runs. Why each rule exists |
| [`references/runners.md`](references/runners.md) | How to wire a review backend: the four questions, plus worked examples |
| [`references/templates/_context.md`](references/templates/_context.md) | Shared context every slice prompt starts with |
| [`references/templates/run-slice.sh`](references/templates/run-slice.sh) | Runs ONE slice: quota guard, idle + hard-cap watchdog, process-group kill, ledger line |
| [`references/templates/chain.sh`](references/templates/chain.sh) | Works the queue unattended; retries on 429, never records a quota error as a report |
| [`references/templates/ORDER.md`](references/templates/ORDER.md) | Tier-order template: what is still covered if the budget dies after tier 2 |

## Install

```bash
git clone https://github.com/Mariomarquezt/sliced-review ~/.claude/skills/sliced-review
```

Then in Claude Code: "review the whole codebase with GLM" / "audit this project with a second model" / `/sliced-review`.

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
