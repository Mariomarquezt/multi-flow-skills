# Keep the prompt cache warm (rule for every skill that waits for a long run)

Added 2026-10-08 (the user). Measured the same day on six test runs.

## The problem

A Claude subagent keeps its prompt cache for **5 minutes** after its last request. The main session
keeps it for 1 hour. When a subagent waits longer than 5 minutes in ONE tool call (a builder, a
reviewer, a test suite, a `codex exec`), its next request writes its WHOLE context again.
Measured: about 150k tokens each time = $0.75 at $5 per 1M (5-minute write). One request that reads
the cache costs about $0.03. Prices: Opus 5.5, confirmed by the user 2026-10-08.

## The rule

**No tool call of a subagent waits longer than 230 seconds.** (the user 2026-10-08: keep 230. The
5-minute timer starts at the previous request, so the model's own writing time and the ssh time
count too. 230 s of wait can be 290 s on the timer.)

1. Start the long command in the background:
   - any command: `~/.claude/skills/multi-model-fix/templates/lean/bg-run.sh <logs dir> <step> -- <command...>`
   - a Devin run: `.../lean/lean-run.sh <mode> <run dir> <brief file> <logs dir> <step>` (sets the tag)
2. Wait in short steps: `.../lean/lean-wait.sh <logs dir> <step>`. It returns after 230 s at most
   and prints `RUNNING` (call it again) or `DONE rc=<n>` + the end of the log.
3. Never `pgrep -f` wait loops (the pattern matches the waiting shell). Never a bare long `sleep`.
4. When the work runs on another machine, copy the scripts there first (`scp`), then call them
   through `ssh`. One `ssh` call per wait.

## Who needs it

- A **subagent** that leads, builds or reviews and waits for a runner or a long test: ALWAYS.
- The **main session** (1-hour cache): not needed for the cache. The background start + done-file
  is still the safe way to wait (no `pgrep` trap, the user can talk while it runs).
- When you brief a subagent that will wait for runs, put this rule and the script paths in the brief.

## It is automatic for every subagent (hook, 2026-10-08)

`~/.claude/hooks/subagent-keepwarm.py` (Mac and laptop, in `~/.claude/settings.json` under
`SubagentStart` and `PreToolUse` / `Bash`; outside this repo) does two things for EVERY subagent,
with or without a skill:

- at the start it puts this rule and the two script paths in the subagent's context;
- it REFUSES a foreground Bash call of a subagent with a timeout above 240 s, and says how to run
  it with `~/.claude/hooks/bg-run.sh` and `~/.claude/hooks/bg-wait.sh` (the same two scripts as
  `lean/bg-run.sh` and `lean/lean-wait.sh`, at a path that does not depend on this repo).

The main session is never touched. Tested live on the laptop 2026-10-08 (rule seen, a 300 s call
refused). A session reads its hooks at start: sessions opened before the install do not have it.

## The other fix (not used)

The user 2026-10-08: stay on the 5-minute cache and keep warm. The setting below is OFF on both machines.

Setting `"subagentPromptCacheTtl": "1h"` in `~/.claude/settings.json` (Claude Code 2.1.242 or
newer) gives subagents the 1-hour cache. Every cache write then costs $8 and not $5 per 1M, and the
setting is ignored while the plan is in overage. The short waits are cheaper; the setting is the
safety net. Which one the user keeps: see `docs/STATUS.md`.
