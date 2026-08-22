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

## Backends wired on this machine

### GLM (z.ai)

```bash
~/.hermes/glm/glm-run.sh "<prompt>" < /dev/null
```

- Model `glm-5.3`, endpoint `https://api.z.ai/api/anthropic`. The paas/v4 endpoint is unfunded —
  never use it.
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
