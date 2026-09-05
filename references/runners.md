# Reference: review backends

Load this in Step 1, when choosing which model does the reviewing.

Every backend below is a **headless one-shot**: you hand it a prompt, it reads files, it prints a
report. None of them are interactive, and all of them are read-only by default — a reviewer must
never be given write tools.

---

## The four questions to answer for ANY backend

Whether it is listed below or brand new, you need these four answers before Step 6:

1. **How do I invoke it with a prompt?** → becomes `RUNNER_CMD` in `runner.env`. Write it as
   `... "$(cat {PROMPT_FILE})"` — the runner substitutes a **path**, never the prompt text,
   because slice briefs contain backticks and `$(...)` that an eval would execute.
2. **Can it tell me how much quota is LEFT?** → becomes `QUOTA_PCT_CMD`, or stays empty.
   Careful: a script that reports what a finished run **cost** is not the same thing and cannot
   guard anything.
3. **Can it tell me what a finished run cost?** → becomes `COST_CMD`, for the ledger.
4. **What does it do when it runs out?** A `429`, a silent truncation, a plain error string?
   The chain greps for this, so know the exact wording.

If a backend is not metered at all, answers 2 and 3 are simply "no". Say so; do not imply a budget
is being managed when it is not.

---

## ROUTE PINNING — read this before writing any `runner.env`

**Several models are reachable by more than one route, and the wrong one is invisible
afterwards.** Nothing in a report says which subscription paid for it. The author's setup has one
correct route per model (adapt the table to your own plans):

| model | CORRECT route | NEVER use |
|---|---|---|
| `gpt-5.6-sol` | **Codex** (`codex exec`) | Cursor's `gpt-5.6-sol-high` / `-xhigh` |
| Grok 4.6 | **Cursor** (`cursor-run.sh --model cursor-grok-4.6-high`) | — |
| Opus 5 | **the user's own Claude Code session** (`Agent` subagent) | Cursor's `claude-opus-5-*` |
| GLM 5.3 Flash | z.ai plan (`glm-run.sh` — flash is the DEFAULT; `--standard` for glm-5.3) | OpenCode Go's `glm-5.3` (returns 174-byte empties) |
| Composer 2.5 | **Cursor** (`cursor-run.sh --model composer-2.5`) | — |

**The Cursor subscription is for GROK and COMPOSER ONLY.** `cursor-run.sh` now
hard-refuses anything else; override is `CURSOR_ALLOW_MODEL=1` and requires asking
the user first -- and when they name a model, still ask whether they want it billed to
Cursor or to its own plan.

Corrected by the author on 2026-08-26 after a kit was wired to the Cursor copies of Sol
and Opus. Do NOT audit this by reading `runner.env` files -- that misses every
ad-hoc call, which is where the spend is. `~/.hermes/cursor/usage.jsonl` showed 25
`claude-opus-5-high` runs (~8.6M tokens) and 4 Sol runs had already gone through
Cursor unnoticed.

**Pin the effort too, and write it in the header.** An inherited effort is invisible
after the fact, which silently breaks any comparison between two runs:

- `codex exec` reads `model_reasoning_effort` from `~/.codex/config.toml` (currently
  `xhigh`). Sol runs across past reviews have drifted medium / high / xhigh with the
  folder name not always saying which.
- `glm-run.sh` set NO effort at all before 2026-08-26 and silently inherited whatever
  `CLAUDE_EFFORT` was in the calling shell. It now pins `high` and takes `--effort`.
- Cursor: the tier IS the model id (`-low` / `-medium` / `-high` / `-xhigh`). Never a
  `-fast` id — `cursor-run.sh` rejects those and exits 1.

Record the route AND the effort in the `runner.env` header and in the `findings.json`
review note, so a reader a month later can tell what actually ran.

## Backends wired on this machine

### GLM (z.ai)

```bash
~/.hermes/glm/glm-run.sh "<prompt>" < /dev/null
```

- **Default model is `glm-5.3-flash`** (author's decision, 2026-08-26). `--standard` selects `glm-5.3`;
  `--flash` still works as a no-op. Endpoint `https://api.z.ai/api/anthropic`. The paas/v4
  endpoint is unfunded — never use it.
- **Effort is pinned `high`** by the script. `--effort <low|medium|high|xhigh|max>` to change it.
  It used to inherit `CLAUDE_EFFORT` silently, which made two runs incomparable after the fact.
- Flash costs exactly **1/3** of glm-5.3 (z.ai multipliers 2.3/0.56/8 vs 6.9/1.7/24), and
  everything outside Mon–Fri 14:00–18:00 Singapore is charged at **50%** on top. Measured: 14
  slices for 8% of a 5-hour LITE window, where glm-5.3 spent 5% on ONE slice.
- Flash's thinking length is variable — usually ~5 min/slice, but one Formitor slice ran past
  10 minutes with nothing written. `glm-run.sh` uses plain `claude -p`, which BUFFERS, so a long
  think is indistinguishable from a hang. Keep `SLICE_IDLE_TIMEOUT` at 1800.
- **Has a real quota endpoint.** `~/.hermes/glm/glm-usage.sh` prints plan, 5-hour window %, weekly %
  and reset times. This is what makes a pre-flight guard possible.
  ```bash
  QUOTA_PCT_CMD='~/.hermes/glm/glm-usage.sh | awk "/5-hour/{for(i=1;i<=NF;i++) if(\$i ~ /%\$/){gsub(\"%\",\"\",\$i); print \$i; exit}}"'
  ```
- Out-of-quota signal: `API Error: Request rejected (429) · [1308][Usage limit reached for 5 hour...]`
- **Reset times in the 429 body are Asia/Shanghai.** Convert to Pacific before quoting them.
- Runs under an isolated `HOME` on purpose — Claude Code ≥2.1.x otherwise prefers a stored Anthropic
  login over the env token and 401s. Do not remove it.
- The `[claude-code:unrecognized_model] glm-5.3` warning is expected and harmless.

### Cursor (Grok 4.6 and Composer 2.5 ONLY)

```bash
~/.hermes/cursor/cursor-run.sh --model cursor-grok-4.6-high "<prompt>"
~/.hermes/cursor/cursor-run.sh --model composer-2.5 "<prompt>"
```

- **The script HARD-REFUSES any model that is not Grok or Composer.** Cursor resells ~204 models
  including `claude-opus-5-*` and `gpt-5.6-sol-*`; those are paid for elsewhere and routing them
  here double-bills invisibly. Override is `CURSOR_ALLOW_MODEL=1`, one run, only after asking the user.
- **Never a `-fast` id** — the script rejects them and exits 1.
- Read-only by default (`--mode ask`). `--write` makes it a real coding agent.
- **No remaining-quota endpoint, and `usage.jsonl` records only `duration_ms` and `prompt_len` —
  no token counts, no cost.** So there is NO pre-flight guard and no percentage to report for a
  Cursor arm. Duration and output size are the only comparable signals. Say so rather than
  implying a budget is being managed.
- **Grok and Composer share ONE quota pool** — never run two Cursor arms concurrently.
- **Grok and Composer never cross-check each other's fixes.** Same subscription, so a fix and its
  check would be on one bill. Five-model ring: Sol → Opus → Grok → GLM Flash → Composer → Sol.
- Grok: use **`-high`, not `-xhigh`**. Measured on 5 slices: xhigh returned 7 findings and zero
  HIGHs against high's 14 and 3, and took 26% longer.
- Composer 2.5 is the fastest reviewer in the stack (~2m/slice) and finds nearly as much, but rates
  almost everything MEDIUM/LOW — good for breadth, unreliable for triage order.

### Kimi (Kimi For Coding)

```bash
KIMI_MODEL=k3-256k ~/.hermes/kimi/kimi-run.sh "<prompt>" < /dev/null
```

- Default model is `kimi-for-coding` (K2.7). Others on the plan: `kimi-for-coding-highspeed`,
  `k3-256k`, `k3`. **Prefer `k3-256k` for review work** — the larger context means fewer truncation
  surprises on a slice with a dozen files.
- Endpoint `https://api.kimi.com/coding`. **Not** `api.moonshot.ai`. An `sk-kimi-*` key is a
  subscription key and Moonshot's open platform rejects it with `Invalid Authentication`. Do not
  "fix" a failure by switching hosts.
- **No remaining-quota endpoint.** `~/.hermes/kimi/kimi-tokens.sh` sums tokens and notional USD from
  the transcript of a run that already finished. Use it as `COST_CMD`, leave `QUOTA_PCT_CMD` empty,
  and let a 429 be the signal.
- Isolated `HOME`, same reason as GLM. The unrecognised-model warning is expected.

### Command Code (multi-model plan)

```bash
~/.hermes/cmd/cmd-run.sh --model <id> "<prompt>"
```

- One subscription fronting several models. Dedicated agent wrappers exist for each:
  `cmd-deepseek-flash` (cheapest, plan default), `cmd-deepseek-pro` (long-context, heaviest),
  `cmd-gpt-luna` (the only OpenAI tier verified working on this plan), `cmd-grok`, `cmd-mimo`,
  `cmd-minimax`, `cmd-muse` (contributor tier, ~95% off — cheapest for a big sweep).
- Read-only by default; `--write` is what enables destructive tools. A reviewer never gets `--write`.
- Useful when one plan is exhausted and the review must continue tonight — same slices, different
  `RUNNER_CMD`.

### Codex (OpenAI)

- Use `codex exec` directly, or the `/codex-audit` skill which already drives multi-round audits.
- **If quota is not the constraint, prefer `/codex-audit` over this skill.** Sliced-review earns its
  keep when the budget is the binding limit or the codebase is too large for one context.
- Always `-m gpt-5.6-sol` for security work — a lighter tier missed three HIGHs on a measured run.
- Always pass `< /dev/null`; `codex exec` hangs on stdin without it.
- **Always pass `-o/--output-last-message` and redirect stdout**, or the slice file is
  30x transcript noise. Without it `codex exec` prints its ENTIRE session to stdout —
  every tool call, every `hook: PostToolUse` line — and then the report TWICE (once
  streamed, once as the final message). Measured 2026-08-26: one Sol slice came out at
  **154,860 bytes where Grok's was 4,988**. The findings were fine; the file was
  unusable for any cross-model comparison and its byte count meant nothing.

  ```bash
  RUNNER_CMD='T="$(mktemp)"; codex exec --skip-git-repo-check -m gpt-5.6-sol \
    -c model_reasoning_effort="xhigh" -s read-only -o "$T" "$(cat {PROMPT_FILE})" \
    < /dev/null > "$T.transcript" 2>&1; cat "$T"; rm -f "$T"'
  ```

  Keep the transcript in a side file rather than discarding it — it is what you read
  when a run misbehaves.

  **Watchdog interaction:** with stdout redirected, NOTHING is written until the run
  ends, so the idle detector cannot see progress and a Codex arm looks hung the whole
  time. Keep `SLICE_IDLE_TIMEOUT` well above the expected slice runtime (1800 for
  4–7 min slices). Lowering it for a Codex arm produces phantom `KILLED_IDLE` results.
- **Salvaging an old run:** the final message starts after the LAST `tokens used\n<count>`
  line in the transcript. A run captured without `-o` does not need repeating.
- The `codex:codex-rescue` subagent is **banned** — it once overwrote committed work.

### Claude subagents

`Agent(subagent_type: "general-purpose")`, one per slice.

- No external quota to manage; the constraint is the session's own budget.
- Only use when the user has asked for it. The point of this skill is usually a **different** pair
  of eyes, and a Claude subagent shares this session's blind spots.

---

## Wiring a backend that is not listed

Answer the four questions, then write `runner.env`. Nothing else in the kit changes — that is the
whole point of keeping the backend in one file.

If the new backend has a quota endpoint, write a one-line adapter that prints **a single integer
0–100 = percent already used**. The runner needs nothing else from it.

Add what you learn to [`../FIELD-NOTES.md`](../FIELD-NOTES.md), especially the exact out-of-quota
wording — the next session greps for it.
