# Reference: review backends

> **Exact model versions live in `models.md` (this folder).** The route table below must use the same ids; when a version changes, change `models.md` first, then the id here.

Load this in Step 1, when choosing which model does the reviewing.

Every backend below is a **headless one-shot**: you hand it a prompt, it reads files, it prints a
report. None of them are interactive, and all of them are read-only by default — a reviewer must
never be given write tools.

**MiMo rule (the user, 2026-10-03): the only MiMo model is MiMo v2.6 Flash.** Never MiMo v2.5 or v2.5 Pro (and no
v2.6 Pro), on any route: Cline, OpenCode Go, Command Code. Use `cline-run.sh --mimo-flash` (works on
the Mac and on the laptop). Every runner refuses any other MiMo id (exit 2). If the asked model cannot run, STOP and
say so; never swap in another model version.

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
5. **Where does it record tokens?** → `USAGE_PROVIDER` in `runner.env`. `usage.py capture` knows
   claude / cline / devin (stderr line), codex (`~/.codex/sessions`), cursor (`$RUNNERS_DIR/cursor/usage.jsonl`),
   cmd (`~/.commandcode/projects`) and every OpenCode-driven runner (`opencode.db`: oc, ocfree,
   xai). A new backend with none of these: make its runner print
   `<name>: usage: in=… cached=… cache_write=… out=…` on stderr and usage.py reads that. Tokens are
   recorded even when the plan is flat or the model free — the API-equivalent price is the comparison.

If a backend is not metered at all, answers 2 and 3 are simply "no". Say so; do not imply a budget
is being managed when it is not.

---

## ROUTE PINNING — read this before writing any `runner.env`

**Several models are reachable by more than one route, and the wrong one is invisible
afterwards.** Nothing in a report says which subscription paid for it. The user has one
correct route per model:

| model | CORRECT route | NEVER use |
|---|---|---|
| `gpt-6.1-sol` (high) | **Codex** (`codex exec`) — swapped in 2026-09-30, replaces `gpt-6-sol` (which replaced `gpt-5.6-sol` on 2026-09-22) | Cursor's `gpt-5.6-sol-*` |
| Grok 4.6 (reviews and judges, from 2026-10-25) | **Cursor** (`cursor-run.sh --model cursor-grok-4.6-high`, inside `hb.sh`) | — |
| Grok 4.7 (multi-fix and multi-build only) | **Cursor** (`cursor-run.sh --model grok-4.7-high`) | never beside a Grok 4.6 arm as independent eyes: same Grok family |
| Opus 5.5 | **The user's own Claude session** (`Agent` subagent) | Cursor's `claude-opus-5-*` |
| MiniMax M3 | **Command Code** (`cmd-minimax`) | OpenCode Go's `--minimax` — same model |
| DeepSeek V4 Pro | **Command Code** (`cmd-deepseek-pro`) | OpenCode Go's `--deepseek-pro` — same model |
| Qwen 3.8 Max | **OpenCode Go** (`oc-run.sh --qwen-max`) | — |
| ClinePass (all 14 ids) | **Cline** (`cline-run.sh --<flag>`) — added 2026-09-26; a SUBSTITUTE bill only, never a pinned route | pairing with the same model on its pinned route: every ClinePass id collides (see "Cline") |
| Laguna S 2.1 / Nemotron 3 Super / dots-3 note (free) | **Cline free** (`cline-run.sh --free-laguna` / `--free-super` / `--free-dots`) — added 2026-09-26, $0 | client, NDA or credential-bearing repos (free pools may log prompts) |
| Composer 2.5 | **Cursor** (`cursor-run.sh --model composer-2.5`) | — |
| Gemini 3.8 Flash | **Cursor** (`cursor-run.sh --gemini`) — added 2026-09-14 | Antigravity's `agy-run.sh --flash` — same model (2026-11-17) |
| Gemini 4 Hydrogen / Carbon / Argon | **Antigravity** (`agy-run.sh --hydrogen` / `--carbon` / `--argon`) — added 2026-11-17 | a Gemini lane checking another Gemini lane's work |
| Muse Spark 1.3 (Cursor copy) | **Cursor** (`cursor-run.sh --muse`) — added 2026-09-14 | never paired with OpenCode Go's `--muse`: same model |
| `gpt-6-luna` (xhigh) | **Codex** (`codex exec -m gpt-6-luna`) — 2026-09-22, replaces Cursor's GPT-5.6 Luna | never checks Sol's work: same Codex pool. Terra is not used |
| Qwen3.7 Plus | **OpenCode Go** (`oc-run.sh --qwen`) | — |
| DeepSeek V4.1 Flash | **OpenCode Go** (`oc-run.sh --deepseek`) | Command Code's `cmd-deepseek-flash` agent is the real V4, one release apart; `cmd-run.sh --model deepseek-v4.1-flash` is the same V4.1 |
| Muse Spark 1.3 | **OpenCode Go** (`oc-run.sh --muse`) — opted in 2026-09-12; the user's OWN code only | any client, NDA or credential-bearing repo |
| Grok 4.6 / 4.7 (xAI copies) | **Cursor stays pinned** (the user 2026-09-16). `xai-run.sh --grok46` (reviews) or `--grok` (fix, build) only as a SUBSTITUTE when Cursor's Grok is spent | never beside a Cursor Grok arm: same model |
| SWE-2 | **Devin** (`devin-run.sh --swe2`) — added 2026-10-06; extra arm, by name only | — (collision-free) |
| Devin copies of Sol 6.1 / Luna 6 / GLM 5.3 Flash / DeepSeek V4.1 Flash, and Fusion (Sol + SWE-2) | **Devin** (`devin-run.sh --sol` / `--luna` / `--glm` / `--deepseek` / `--fusion`) — a SUBSTITUTE bill only | pairing with the same model on its pinned route; Fusion counts as Sol |
| Grok 4.5 | **Command Code** (`cmd-grok`) | `xai-run.sh --grok45` — same model |
| Grok 4.3 / grok-build-0.1 / grok-4.20 reasoning | **xAI** (`xai-run.sh --grok43` / `--build` / `--grok420`) — added 2026-09-16 | never as independent eyes beside any other Grok arm |

**The Cursor subscription is for GROK, COMPOSER, GEMINI 3.8 FLASH and MUSE SPARK 1.3** (widened by
The user 2026-09-14; Sol and Opus stay refused; Luna moved to Codex as GPT-6 Luna on 2026-09-22). `cursor-run.sh` now
hard-refuses anything else; override is `CURSOR_ALLOW_MODEL=1` and requires asking
The user first -- and when he names a model, still ask whether he wants it billed to
Cursor or to its own plan.

Corrected by the user on 2026-08-26 after a kit was wired to the Cursor copies of Sol
and Opus. Do NOT audit this by reading `runner.env` files -- that misses every
ad-hoc call, which is where the spend is. `$RUNNERS_DIR/cursor/usage.jsonl` showed 25
`claude-opus-5-high` runs (~8.6M tokens) and 4 Sol runs had already gone through
Cursor unnoticed.

**Pin the effort too, and write it in the header.** An inherited effort is invisible
after the fact, which silently breaks any comparison between two runs:

- `codex exec` reads `model_reasoning_effort` from `~/.codex/config.toml` (currently
  `high`, default model `gpt-6-luna`) — always pass `-m` and the effort. Sol runs across past reviews have drifted medium / high / xhigh with the
  folder name not always saying which.
- Cursor: the tier IS the model id (`-low` / `-medium` / `-high` / `-xhigh`). Never a
  `-fast` id — `cursor-run.sh` rejects those and exits 1.

Record the route AND the effort in the `runner.env` header and in the `findings.json`
review note, so a reader a month later can tell what actually ran.

## Backends wired on this machine

### Cursor (Grok 4.7, Composer 2.5, Gemini 3.8 Flash, Muse Spark 1.3)

```bash
$RUNNERS_DIR/cursor/cursor-run.sh --model grok-4.7-high "<prompt>"
$RUNNERS_DIR/cursor/cursor-run.sh --model composer-2.5 "<prompt>"
```

- **Added 2026-09-14 (the user):** `--gemini` (`gemini-3.8-flash-high`), `--muse` (`muse-spark-1.3-high`),
  `--luna` (`gpt-5.6-luna-high`, NOT used by the skills since 2026-09-22 — Luna runs on Codex as GPT-6 Luna). All at `-high`, all verified on a planted bug. Also `--grok` and
  `--composer` shortcuts. **Only `--gemini` is collision-free** — `--muse` is the same model as
  OpenCode Go's `--muse`, `--luna` is the same model as `cmd-gpt-luna`. All five Cursor models share
  ONE quota pool and none may cross-check another Cursor model's fix. Cursor's data handling for its
  Muse copy has not been checked against OpenCode Go's training opt-in — do not assume either way.
- **The script HARD-REFUSES every other model, including Sol and Opus.** Cursor resells ~204 models
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

### Command Code (multi-model plan)

```bash
$RUNNERS_DIR/cmd/cmd-run.sh --model <id> "<prompt>"
```

- One subscription fronting several models. Dedicated agent wrappers exist for each:
  `cmd-deepseek-flash` (cheapest, plan default), `cmd-deepseek-pro` (long-context, heaviest),
  `cmd-gpt-luna` (the only OpenAI tier verified working on this plan), `cmd-grok`, (`cmd-mimo` REMOVED 2026-10-03, MiMo v2.5 is banned),
  `cmd-minimax`, `cmd-muse` (contributor tier, ~95% off — cheapest for a big sweep).
- Read-only by default; `--write` is what enables destructive tools. A reviewer never gets `--write`.
- Useful when one plan is exhausted and the review must continue tonight — same slices, different
  `RUNNER_CMD`.
- **Account pool (2026-09-17):** `cmd-run.sh` now runs through `$RUNNERS_DIR/cmd/cmd-pool.py`, which
  picks the Command Code account with the most room and re-runs on the next account when one runs out.
  `--account <name>` pins; `--distinct` gives each PARALLEL run its own subscription (exit 75 if none
  free). Several accounts = several separate quota pools, but the SAME model family — a second
  account is not a second pair of eyes. `cmd-pool.py status` = live 5h/weekly/monthly per account
  (QUOTA source for this route). Exit 75 = every account out.

### Cline

```bash
$RUNNERS_DIR/cline/cline-run.sh --mimo-flash "<prompt>" < /dev/null
$RUNNERS_DIR/cline/cline-run.sh --write --glm "<prompt>" < /dev/null
$RUNNERS_DIR/cline/cline-quota.py          # 5h / 7d / 30d spend vs caps
```

- Added 2026-09-26. The user's **ClinePass** ($9.99/mo, period ends on the 26th) on the `cline` npm CLI
  (`npm i -g cline`, v3.0.65, binary lands in `$RUNNERS_DIR/node/bin/cline`). OAuth login via
  `cline auth` → "Sign in with ClinePass"; tokens live in `~/.cline/data/settings/providers.json`
  (never print it). The CLI refreshes the token itself on each run.
- **Roster, all verified 2026-09-26 with a read (plan) AND a write (`--write`) probe on a planted bug:**

  | flag | id | collision |
  |---|---|---|
  | `--mimo-pro` | `cline-pass/mimo-v2.6-pro` | BANNED 2026-10-03 (the user: MiMo v2.6 Flash only); refused by the runner |
  | `--mimo-flash` | `cline-pass/mimo-v2.6-flash` | **default since 2026-10-03, the ONLY MiMo allowed**; = OC `--mimo-flash` |
  | `--mimo25-pro` | `cline-pass/mimo-v2.5-pro` | BANNED 2026-10-03 (the user: MiMo v2.6 Flash only); refused by the runner |
  | `--mimo25` | `cline-pass/mimo-v2.5` | BANNED 2026-10-03 (the user: MiMo v2.6 Flash only); refused by the runner |
  | `--deepseek-pro` | `cline-pass/deepseek-v4-pro` | = `cmd-deepseek-pro`, OC |
  | `--deepseek` | `cline-pass/deepseek-v4.1-flash` | = OC `--deepseek` |
  | `--glm` | `cline-pass/glm-5.3` | = OC `--glm-std` |
  | `--glm-flash` | `cline-pass/glm-5.3-flash` | = OC `--glm` |
  | `--minimax` | `cline-pass/minimax-m3` | = `cmd-minimax`, OC |
  | `--muse` | `cline-pass/muse-spark-1.3-contributor` | = OC `--muse` (+ Cursor) |
  | `--qwen-max` | `cline-pass/qwen3.8-max` | = OC `--qwen-max` |
  | `--qwen37-max` | `cline-pass/qwen3.7-max` | — |
  | `--qwen-plus` | `cline-pass/qwen3.7-plus` | = OC `--qwen` |

  Free ($0, Cline account, upstream OpenRouter `:free` pools):

  | flag | id | note |
  |---|---|---|
  | `--free-laguna` | `poolside/laguna-s-2.1:free` | collision-free |
  | `--free-super` | `nvidia/nemotron-3-super-120b-a12b:free` | collision-free |
  | `--free-dots` | `dots-studio/dots-3-note-preview:free` | collision-free |
  | `--free-ultra` | `nvidia/nemotron-3-ultra-550b-a55b:free` | = OpenCode free `nemotron-3-ultra-free` |
  | `--free-north` | `cohere/north-mini-code:free` | = OpenCode free `north-mini-code-free` |
  | `--free-laguna-xs` | `poolside/laguna-xs-2.1:free` | flaky: 404'd in the probe, passed on rerun |
  | `--free-bunny` | `stealth/space-bunny-alpha` | STEALTH = unknown lab; never a cross-check |
  | `--free-router` | `openrouter/free` | random free model per call; never a cross-check |

  Probe timings (tiny task): read 3–24s (Laguna S 52s), write 7–60s. `qwen/qwen3.8-27b:free`,
  `google/gemma-4-31b-it:free` and `thinkingmachines/inkling*:free` 429'd upstream on 2026-09-26;
  reachable via `--model <id>` when the pool is free. Full catalog: 458 ids (OpenRouter mirror) at
  `GET https://api.cline.bot/api/v1/ai/cline/models` with the bearer token. [hypothesis] non-free
  ids bill the Cline credit balance (~$0.005 on 2026-09-26), NOT ClinePass — do not use them.
- **Read-only = Cline plan mode (`-p`).** [fact 2026-09-26] Plan mode still has `run_commands` and
  used it (`ls`, `pwd`); asked to `touch` a file, and to run a disguised
  `python3 -c "open(...,'w')"`, it refused both and no file appeared. [hypothesis] the block is the
  model obeying plan-mode rules, not a sandbox. For untrusted prompts run in a throwaway worktree.
- **Output:** the runner runs `cline --json`, prints only the final answer to stdout, one
  `cline-run: [tool N] <name>` line per tool call plus a `... working` line every 30s of streaming to
  stderr, and a closing usage line (`in/out/cached/cost/ms`). Exit 3 = `finishReason` not
  `completed` (upstream error, empty answer); exit 1 = no result at all. `--raw` = Cline's own
  styled stream. `--thinking none|low|medium|high|xhigh` passes through.
- **A one-word prompt is parsed as a subcommand.** [fact 2026-09-26] `cline "hi"` →
  "Unknown command or unquoted prompt". Real review/fix prompts are never one word; do not probe
  with one.
- **TERM kills cline too.** [fact 2026-09-26] The pipeline runs in the background with a TERM trap,
  so the sliced-review watchdog's kill leaves no orphan `cline` (verified 0 left after `kill -TERM`).
- **Quota:** `QUOTA_PCT_CMD='$RUNNERS_DIR/cline/cline-quota.py --pct'` prints the WORST window as %.
  Caps come from `GET /api/v1/users/me/plan` → `entitlements.cline_pass.inferenceCapThreshold`.
  [hypothesis 2026-09-26] units are 1e-8 USD (a logged call matched list price), so the caps read
  **$10 / 5h, $25 / 7d, $50 / 30d**. Spend = sum of `costUsd` for `aiModelTypeName=cline-pass` from
  `GET /api/v1/users/<id>/usages?limit=1000`. **That list returns at most 200 calls and ignores
  every paging param tried**, so past ~200 calls in a window the % reads LOW (the script warns).
  Treat MAX_PCT as a floor, not a ceiling; a 429 is still the real out-of-quota signal.
  `COST_CMD` stays EMPTY: `run_result.totalCost` is always 0 on ClinePass.
- Parallel runs are fine: 6 at once, 44 probe runs, no lock or state errors.
- **The hub daemon dies if its start folder is deleted.** [fact 2026-09-26, laptop] Every `cline`
  run talks to ONE background `cline --cline-hub-daemon`, started in the cwd of the FIRST run.
  Deleting that folder (a /tmp probe dir) later crashes the daemon (Bun panic
  `CurrentWorkingDirectoryUnlinked`) and EVERY running Cline task ends at once with
  `session not found` (exit 1, no edits). Before a long run: `pkill -f "[c]line-hub-daemon"`, then
  one tiny run from `~` so the daemon lives in a folder that is never removed. Laptop Cline set up
  2026-09-26 (npm prefix `$RUNNERS_DIR/node`, device-code login via the browser).
- **Data policy unknown.** [hypothesis] ClinePass routes through Vercel's AI gateway to the model
  vendors (usage rows show `aiInferenceProviderName: vercel`, provider order deepseek/alibaba).
  The user's own code, not client/NDA/credential-bearing repos, until confirmed.
  Free models: assume prompts are logged.

### OpenCode Go

```bash
$RUNNERS_DIR/opencode/oc-run.sh --qwen "<prompt>"
$RUNNERS_DIR/opencode/oc-run.sh --model opencode-go/<id> "<prompt>"
```

- The user's paid OpenCode Go plan. Wired into these skills 2026-09-12; before that it existed on the
  machine but was NOT a backend here.
- Auth is an API key the CLI stores under the `opencode-go` provider in
  `~/.local/share/opencode/auth.json`. **There is no env var and no base URL to override**, so this
  backend cannot follow the GLM pattern of pointing `ANTHROPIC_BASE_URL` elsewhere.
- Read-only is the built-in `plan` agent. `--write` swaps to `build` + `--auto`. A reviewer never
  gets `--write`.
- **ROSTER (the user, 2026-09-12), with short flags on the runner. All eleven verified end-to-end:**

  | flag | id | model | collision |
  |---|---|---|---|
  | `--qwen` | `qwen3.7-plus` | Qwen3.7 Plus | **none — safest pick** |
  | `--qwen-max` | `qwen3.8-max` | Qwen 3.8 Max | **none** |
  | `--qwen-flash` | `qwen3.8-flash` | Qwen 3.8 Flash | Command Code `qwen3.8-flash` |
  | `--glm` | `glm-5.3-flash` | GLM 5.3 Flash | Command Code, Cline, Devin — same model |
  | `--glm-std` | `glm-5.3` | GLM 5.3 standard | Cline `--glm` |
  | `--deepseek` | `deepseek-v4.1-flash` | DeepSeek V4.1 Flash | Command Code, Cline, Devin — same model |
  | `--deepseek-pro` | `deepseek-v4-pro` | DeepSeek V4 Pro | `cmd-deepseek-pro` |
  | `--mimo` | `mimo-v2.5-pro` | MiMo v2.5 Pro | BANNED 2026-10-03 (the user: MiMo v2.6 Flash only); refused by the runner. Use `--mimo-flash` (`opencode-go/mimo-v2.6-flash`, added 2026-10-03, NOT probed) |
  | `--minimax` | `minimax-m3` | MiniMax M3 | `cmd-minimax` |
  | `--muse` | `muse-spark-1.3-contributor` | Muse Spark 1.3 | data-sharing opt-in, below |

  **Only `--qwen` and `--qwen-max` are collision-free.** Everything else duplicates a model the user
  already pays for elsewhere.
- **`glm-5.3` (`--glm-std`) WORKS.** This file long carried a warning that OpenCode Go's `glm-5.3`
  "returns 174-byte empties". Retested 2026-09-12 on a planted bug: it answered correctly. That
  warning is **retired** — do not reinstate it from an older note.
- **The Muse opt-in is per WORKSPACE, not per account.** The user opted in, then rotated the OpenCode
  Go key; the new key belongs to a different workspace (`wrk_01M01PFG…` vs `wrk_01KTZ8YD…`) and
  `--muse` was blocked again until he opted in there too. **A key rotation can silently revoke a
  model.** Re-probe `--muse` after any key change rather than assuming the grant carried over.
- **`opencode models` WAS wrong earlier on 2026-09-12 and has since corrected itself.** At the
  first check it omitted `deepseek-v4.1-flash` (which ran fine) and listed
  `opencode-go/deepseek-flash` (which returned `500 Unexpected server error`);
  `https://models.dev/api.json` was right where the CLI was wrong. Re-listed after the key swap:
  `deepseek-v4.1-flash` is now present and the broken `deepseek-flash` is gone, so the list is
  currently accurate. **The lesson stands even though this instance healed: the list is a cache and
  can disagree with reality in BOTH directions — probe an id before trusting its presence or its
  absence.**
- **`--muse` works as of 2026-09-12 — the user completed the data-sharing opt-in himself.** Read that
  as the caution going LIVE, not as it being cleared: the contributor tier is cheap BECAUSE it
  retains prompts for training, and every call now feeds that. **Restrict `--muse` to the user's own
  code.** Never give it a client repository, NDA material, or a file holding credentials — and a
  sliced review is exactly where this goes wrong, because a slice file list is assembled
  mechanically and nothing in it flags whose code it is. When a queue spans client work, run it on
  a different arm rather than trimming slices. `muse-spark-1.2-contributor` shares the opt-in.
- **SAME-MODEL TRAPS — the reason this backend needs care.** "Different subscription" is the usual
  proxy for "different eyes", and on this plan that proxy breaks:
  - `--glm` **IS** GLM 5.3 Flash, the same model as the Command Code, Cline and Devin copies, and a
    member of the `5` ring. Another route just moves the bill.
  - `--deepseek` is V4.1 — the SAME model as the Command Code, Cline and Devin copies, and one
    point release off Command Code's `cmd-deepseek-flash` (the real V4).
  - `--glm-std` **IS** Cline's `--glm` (plain GLM 5.3); `--deepseek-pro` **IS** `cmd-deepseek-pro`;
    `--minimax` **IS** `cmd-minimax`;
  - `--mimo` (v2.5 **Pro**) is one tier above `cmd-mimo` (plain v2.5) —
    close family, still weak as "independent" eyes.

  None of those pairs may be a fix and its cross-check, a build and its review, or two
  "independent" reviewers in one scorecard. Pick ONE route per model per run and write it in the
  `runner.env` header.
- **No remaining-quota endpoint and no per-run cost figure.** `QUOTA_PCT_CMD` and `COST_CMD` stay
  EMPTY. Say so rather than implying a budget is being managed.
- `oc-run.sh` STREAMS, unlike the buffered `claude -p` backends, so the idle watchdog can see real
  progress — `SLICE_IDLE_TIMEOUT` need not be inflated the way it must be for Codex.
- Free tier lives under the `opencode/` provider (not `opencode-go/`) and costs no plan credits:
  `deepseek-v4-flash-free`, `mimo-v2.5-free`, `hy3-free`, `nemotron-3-ultra-free`,
  `north-mini-code-free`, `big-pickle`. Use for throwaway work.
  2026-10-17 probe (all answered OK): `beam-free` (Beam, new), `nemotron-3.5-super-vl-free`,
  `deepseek-v4.1-flash-free`, `glm-5.3-flash-free` — free for now. Also listed: `mimo-v2.6-flash-free`,
  `longcat-2.5-preview-free`, `nemotron-3.5-lightning-free`. Short flags (oc-run.sh + pi-run.sh): `--beam`, `--nemotron-vl`, `--deepseek-free`, `--glm-free`.
  TRAP: the free tier returns 403 FreeTierError to any app but OpenCode, so pi-run.sh execs oc-run.sh for `opencode/*-free`.
  2026-11-05 (the user): `pulse-alpha-free` (Pulse, stealth) and `crouton-alpha-free` added; lanes `pulse` + `crouton`
  (Crouton runs on OpenRouter free through `$RUNNERS_DIR/openrouter/or-free-run.sh`, which refuses any model whose price is not $0).
  See models.md "Free stealth lanes".

### xAI (Grok, the user's xAI plan)

```bash
$RUNNERS_DIR/xai/xai-run.sh --grok "<prompt>"
$RUNNERS_DIR/xai/xai-run.sh --model xai/<id> "<prompt>"
```

- **Wired 2026-09-16.** The user connected his xAI subscription to OpenCode himself, by OAuth. Auth is
  stored under the `xai` provider in `~/.local/share/opencode/auth.json`. No env var, no key file,
  no base URL. The runner drives opencode, so it streams like OpenCode Go.
- **Read-only is the built-in `plan` agent.** `--write` swaps to `build` + `--auto`. A reviewer
  never gets `--write`.
- **ROSTER, all five verified 2026-09-16** on a planted two-bug file. Every arm found both bugs.
  `--grok` moved to Grok 4.7 on 2026-09-21 (the user); 4.7 passed only a PONG probe, so its review
  quality and speed are UNMEASURED. `--grok46` keeps the old 4.6 arm:

  | flag | id | effort | time | collision |
  |---|---|---|---|---|
  | `--grok` | `grok-4.7` | high | not measured | **IS Cursor's pinned Grok 4.7** |
  | `--grok46` | `grok-4.6` | high (offers low..xhigh) | 14s | same Grok family (old pinned model) |
  | `--grok45` | `grok-4.5` | high (up to high) | 15s | **IS `cmd-grok`** |
  | `--grok43` | `grok-4.3` | high (none..high) | 14s | same Grok family |
  | `--build` | `grok-build-0.1` | no variants | 34s | same Grok family |
  | `--grok420` | `grok-4.20-0309-reasoning` | no variants | 16s | same Grok family |

  **[retracted 2026-09-16] "grok-build-0.1 was the most thorough"** — that came from ONE run on an
  11-line file with 2 planted bugs. Every arm found the same 2 real bugs. grok-build also listed 5
  extra items (missing input guards, a side effect of the bug already found). Those are style notes,
  not more real bugs, and one run is no evidence. Its only measured difference: it took 34s where the
  others took 14–16s. Its review quality is UNTESTED on real code.
- **Cursor stays the PINNED Grok 4.7 route** (the user's choice, 2026-09-16). Use `--grok` only as a
  substitute when Cursor's Grok is spent, and write that swap in the `runner.env` header.
- **!! EVERY ARM ON THIS PLAN IS GROK.** Nothing here is independent of the Grok already in the core
  three. No xAI arm may cross-check or review a Cursor Grok arm's work. No xAI arm counts as a
  separate reviewer beside a Cursor Grok arm or `cmd-grok` in one scorecard.
- **Use `high`, not `xhigh`.** The runner pins `high` for 4.6, 4.5 and 4.3. On Cursor, Grok at
  `xhigh` found fewer HIGHs than at `high` and ran 26% longer. `--variant <level>` overrides it.
- **Not usable:** `grok-4.20-multi-agent-0309` fails with `Client-side tools for multi-agent models
  require beta access`. `grok-4.20-0309-non-reasoning` answers, but it does not think, so do not
  use it for review. The `grok-imagine-*` ids are image and video models, not chat.
- **No remaining-quota endpoint and no per-run cost.** `QUOTA_PCT_CMD` and `COST_CMD` stay EMPTY. The
  out-of-quota wording is not known yet. Record it in `../FIELD-NOTES.md` the first time it shows.
- **The laptop needs its own login.** The OAuth token is not copied between machines, because a
  refresh on one machine can invalidate the other. Run `opencode auth login` on the laptop.

### Antigravity (Gemini, the user's Google AI Ultra plan)

```bash
$RUNNERS_DIR/antigravity/agy-run.sh --carbon "<prompt>"          # read-only review
$RUNNERS_DIR/antigravity/agy-run.sh --write --carbon "<prompt>"  # fixer / builder
$RUNNERS_DIR/antigravity/agy-run.sh --model gemini-4-hydrogen-xhigh "<prompt>"
```

- **Wired 2026-11-17.** Auth = the user's own `agy` login (Google account, macOS Keychain). No env
  var, no key file. Log in on each machine with `agy`; never copy the token. CLI 1.5.10.
- **Gemini only (the user, 2026-11-17).** Flags: `--hydrogen` (`gemini-4-hydrogen-high`, also
  `-low/-medium/-xhigh`), `--carbon` (`gemini-4-carbon-high`, default), `--argon`
  (`gemini-4-argon-high`), `--flash` (`gemini-3.8-flash-high`). Any non-`gemini-*` id and
  `gemini-pro-orchestrator*` exit 2.
- **Read-only** = `--mode plan` + `--settings '{"permissions":{"allow":["read_file(*)"],"deny":["write_file(*)"]}}'`.
  Plan mode denies every shell command, so the runner appends "read files with your file tool, not
  shell commands" to the prompt. Without the `read_file(*)` allow, the model tried `ls`, was denied,
  and stopped after one turn with no review. Tested: told to fix, it wrote a plan only; md5 unchanged.
- **`--write`** = `--mode accept-edits --sandbox` + allow `read_file(*)`, `command(*)`. Without the
  `command(*)` allow, headless `-p` auto-denies every command ("a tool required the command
  permission that headless mode cannot prompt for") and the fixer changes nothing. `--sandbox` keeps
  those commands inside agy's terminal sandbox. **Never `--dangerously-skip-permissions`.**
- **Trap:** `-p` takes the NEXT word as its prompt. `agy -p --mode plan ...` fails ("-p took --mode
  as its prompt"). Put `-p "<prompt>"` LAST. The runner does this.
- **Output:** the runner asks for `--output-format json`, prints only the answer on stdout, and
  writes `agy-run: usage: in=.. cached=.. out=.. thinking=.. model=.. secs=.. conv=.. status=..` on
  stderr plus a line in `$RUNNERS_DIR/antigravity/usage.jsonl`. Exit 1 when status is not `SUCCESS`.
  Denied tool calls are printed as `agy-run: denied actions: [...]`.
- **Quota:** `codexbar usage --provider antigravity` (key `antigravity` in `pick-provider.py`):
  5-hour + weekly Gemini windows. Per-run cost: none (plan). Out-of-quota wording not seen yet;
  record it in `../FIELD-NOTES.md` the first time it shows.
- **Measured 2026-11-17 (planted two-bug file):** Carbon high, read-only: found both bugs + 2 guard
  notes, 3 min 42 s, 45k tokens (12k thinking). Flash medium, write: fixed both and ran the node
  check, 7–20 s. Review quality on real code: NOT measured.
- **Same-model trap:** `--flash` IS Cursor's `--gemini`. All four flags are Gemini: none checks
  another Gemini lane's work, and two of them never count as two reviewers in a scorecard.
- **Mac only today.** The laptop has no `agy` (checked 2026-11-17). Install and log in there before
  any laptop lane uses it.

### Devin (Devin Pro: SWE-2, Fusion, resold models)

**Added 2026-10-08:** `--continue` (= `devin -c`) goes on with the most recent conversation of the
CURRENT directory: the helper keeps its context and its cache (probe: a word given in run 1 came
back in run 2). One worktree per helper, never `--continue` in a directory another run used. A
continued conversation exports all its requests again; the runner counts only the new ones (state
in `$RUNNERS_DIR/devin/.cont/`). `DEVIN_RUN_TAG=<text>` in the environment is logged as `tag`, with
`secs` (wall time); sum one skill run with `devin-usage.py --tag <text>`. The session model's own
tokens: `$RUNNERS_DIR/scripts/claude-usage.py --session <id> --since <ISO>`. Lean lane and run rules:
`lean-lane.md`.


```bash
$RUNNERS_DIR/devin/devin-run.sh --swe2 "<prompt>"
$RUNNERS_DIR/devin/devin-run.sh --write --fusion "<prompt>"
```

- **Wired 2026-10-06.** The user's Devin Pro plan (upgraded from Free that day). Login is his own
  (`devin auth login`, browser); credentials in `~/.local/share/devin/credentials.toml` (never print).
  **The `devin` binary is NOT on PATH**: the installer links only `devin-desktop` (the editor). The
  CLI is `/Applications/Devin.app/Contents/Resources/app/extensions/windsurf/devin/bin/devin`; the
  runner uses that path. Mac only; the laptop needs its own install and login.
- **An extra arm, by name only.** Not a member of the core three or the `5` ring.
- **ROSTER (the user's pick 2026-10-06), each verified with a read probe on a planted two-bug file:**

  | flag | id | probe | collision |
  |---|---|---|---|
  | `--swe2` | `swe-2-high` | 34s, both bugs | **default; none. The only new eyes here.** Listed "Free" on Pro |
  | `--sol` | `gpt-6-1-sol-medium` | 23-27s, both bugs | **IS Codex `gpt-6.1-sol`** (the PINNED Sol route) |
  | `--luna` | `gpt-6-luna-medium` | 29s, both bugs | **IS Codex `gpt-6-luna`** |
  | `--glm` | `glm-5-3-flash-max` | 32s, both bugs | **IS GLM 5.3 Flash** = OC, Command Code, Cline |
  | `--deepseek` | `deepseek-v4-1-flash-high` | 12s, both bugs | **IS OC `--deepseek`**, Command Code, Cline |
  | `--fusion` | `fusion-gpt-6-1-sol-high-sidekick-swe-2-medium` | 21s, both bugs | counts as **Sol** |
  | `--swe17` | `swe-1-7` (SWE-1.7 Max; `--model swe-1-7-medium` also allowed) | answered, 2026-10-06 | none; Cognition's older model. Docs: free |
  | `--glm52` | `glm-5-2` (GLM-5.2 High, the only free GLM-5.2 id) | answered, 2026-10-06 | older GLM, same family as GLM 5.3. Docs: free |

  `--effort <level>` swaps the effort part of the id. Sol and Luna: low, medium, high, xhigh, max.
  SWE-2: medium, high, max. GLM Flash: low, high, max. DeepSeek V4.1 Flash: high, max.
- **Fusion = two models in ONE run.** A lead model plans, writes the brief and reviews the diff; a
  cheaper "sidekick" does the hands-on reading, editing and test runs. The id carries both:
  `fusion-<lead>-sidekick-<sidekick>`. **The user's rule 2026-10-06: lead = GPT-6.1 Sol ONLY, sidekick =
  SWE-2 ONLY.** The runner refuses every other pair. Billed at the lead's price.
- **The account allows 700+ ids, most paid per token, Fable included.** The runner REFUSES anything
  outside the roster (exit 2); `DEVIN_ALLOW_MODEL=1` lifts that for one run, only after asking the user.
  Fable, Opus 5 and older, and `-priority` / `-fast` ids are refused always.
- **Read-only = `--permission-mode auto`, a real block.** [fact 2026-10-06] In print mode a file
  write and a `touch` were both rejected by the CLI ("rejected a tool call that requires
  confirmation"). `--write` = `dangerous` (edits AND commands). `accept-edits` can edit but cannot
  run a command in print mode, so a fixer could not run its tests; not used.
- **Exit code is 0 even when a tool call was rejected, and even on an EMPTY answer.** [fact
  2026-10-06] One `--sol` read run returned 0 bytes, exit 0, in 16s; two reruns were fine. Judge by
  the result line (`TOTAL FINDINGS`) and the files; retry once on an empty file.
- **A fresh upgrade takes minutes to reach the CLI.** [fact 2026-10-06] ~15 min after the upgrade,
  `auth status` said Pro but every model answered `Error: Upgrade to Pro to access this model`. It
  cleared by itself a few minutes later. That wording = plan not seen yet, not a bad id.
- **`swe-1-6-slow` (the Free-plan model) is gone on Pro** (`Unknown model`). Pro lists `swe-1-6`.
- **Tokens: yes. Cost: estimate only.** Print mode shows no usage, but the `--export` file holds
  the tokens of every request. The runner reads it and prints one stderr line:
  `devin-run: usage: requests=… in=… cached=… out=… max_req=… est_usd=…`. Devin reports NO cost;
  `est_usd` is the runner's own sum, priced per request from **`$RUNNERS_DIR/devin/prices.json`**
  (edit prices THERE, nothing else). Fusion = `n/a` (two models, two prices, one total).
  [fact 2026-10-06] Every request carries ~18k input tokens of overhead: a one-line Sol answer
  costs about $0.035.
- **Prices (the user 2026-10-06, from https://docs.devin.ai/desktop/models, self-serve):** Devin bills
  each model at its provider's own token price. Per 1M, input / cached / output: Sol 6.1
  $2 / $0.10 / $10; Luna 6 $0.10 / $0.01 / $0.50; GLM 5.3 Flash $0.15 / $0.029 / $0.50; DeepSeek
  V4.1 Flash $0.22 / $0.01 / $0.66. **SWE-2 is free only through 2026-10-15**, then $3 / $0.30 / $15
  (the price file switches by date). SWE-1.7 and GLM-5.2 High: the docs table shows no price
  (the user reads that as free) but `devin models list` still prints one. [hypothesis] free; not
  confirmed on a bill. Sol 6.1 and DeepSeek V4.1 Flash are not on the docs page; their prices come
  from `devin models list`.
- **!! 272K rule (GPT Sol and Luna).** When ONE request has more than 272K prompt tokens (uncached
  + cached), the WHOLE request is billed at about double (Luna $0.20 / $0.02 / $0.75; Sol
  $4 / $0.40 / $15; Sol 6.1 rates assumed equal to Sol 6). **Keep every Devin Sol / Luna slice and
  brief well under 272K** (the user 2026-10-06): small file lists, no whole-repo prompts. The usage
  line prints `max_req` and a `!!` warning when a request crossed the limit. SWE-2 context is 262K.
- **Usage log + report (2026-10-06).** Every `devin-run.sh` run appends one line to
  `$RUNNERS_DIR/devin/usage.jsonl` (time, model, mode, exit, in / cached / out tokens, est_usd, cwd).
  `$RUNNERS_DIR/devin/devin-usage.py [--week | --month | --days N | --all]` prints tokens per model.
  It counts runner runs only, not the Devin app or a plain `devin` call. `COST_CMD` can read the
  last line of that file.
- **No remaining-quota command** for headless use (`/usage` and `/session-stats` are in-session
  slash commands). `QUOTA_PCT_CMD` stays EMPTY.
- **Telemetry is ON and the data policy is unknown.** [hypothesis] the user's own code only, not
  client/NDA/credential-bearing repos, until confirmed.
  [self_report 2026-10-06] the user turned ON the account setting "disable training" ("don't share data to help
  improve Devin") and accepts that. [fact 2026-10-06 01:06 PT] `~/.cache/devin/telemetry_state.json` still said
  `is_zdr = False` (zero data retention NOT active: prompts may be kept, only not used for training). Rule stays:
  The user's own code only.
- **!! Devin imports Claude's MCP servers, hooks, rules and skills by default** (`read_config_from`,
  also Cursor, OpenCode, Windsurf, Zed). [fact 2026-10-06] A plain `devin -p` run started the user's
  hermes, n8n, WordPress, Supabase and Cloudflare MCP servers, about 25 processes, and the model
  could call them. With `dangerous` that is fleet and messaging access for a builder. The runner
  passes `--config $RUNNERS_DIR/devin/runner-config.json` (every import `false`; `mcp list` = none) and
  refuses to run without that file. **Never call the `devin` binary directly for a skill run.**
  The Devin DESKTOP app does the same import and keeps those servers running while it is open.
- **Fusion write probe** [fact 2026-10-06]: fix + test on the planted file, PASS, 98s (plain SWE-1.6
  did it in 12s). The export showed two sidekick handoffs (reproduce, then fix). Slow on tiny jobs.
- First run edits `~/.zshrc` (a "MANAGED DEVIN BLOCK" that adds `~/.local/bin` to PATH).

### Codex (OpenAI)

- **Swift builds go through OpenCode, not `codex exec`** (2026-09-30). The Codex sandbox nests
  `sandbox-exec` and blocks `~/Library` caches + network, so `swift build` fails there. For any Sol
  job that builds or runs Swift: `$RUNNERS_DIR/opencode/oc-run.sh --sol --write "$(cat brief)" < /dev/null`
  (`openai/gpt-6.2-sol`, variant high, ChatGPT plan via OpenCode OAuth in
  `~/.local/share/opencode/auth.json`). Same model as Codex-Sol: never a fix and its cross-check.
  OpenCode lists no GPT-6 Luna, so Luna has no Swift-build route. Probe: `swift build` +
  `PROKIT_ONLY=mkD swift run ProKitTests`, exit 0, 31 s.
- Use `codex exec` directly, or the `/codex-audit` skill which already drives multi-round audits.
- **If quota is not the constraint, prefer `/codex-audit` over this skill.** Sliced-review earns its
  keep when the budget is the binding limit or the codebase is too large for one context.
- Always `-m gpt-6.2-sol` (high) for security work — a lighter tier missed three HIGHs on a measured run.
- Always pass `< /dev/null`; `codex exec` hangs on stdin without it.
- **Always pass `-o/--output-last-message` and redirect stdout**, or the slice file is
  30x transcript noise. Without it `codex exec` prints its ENTIRE session to stdout —
  every tool call, every `hook: PostToolUse` line — and then the report TWICE (once
  streamed, once as the final message). Measured 2026-08-26: one Sol slice came out at
  **154,860 bytes where Grok's was 4,988**. The findings were fine; the file was
  unusable for any cross-model comparison and its byte count meant nothing.

  ```bash
  RUNNER_CMD='T="$(mktemp)"; codex exec --skip-git-repo-check -m gpt-6.2-sol \
    -c model_reasoning_effort="high" -s read-only -o "$T" "$(cat {PROMPT_FILE})" \
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

`Agent(subagent_type: "general-purpose")`, one per slice, with `model:` set to the arm (`opus` /
`sonnet`).

- No external quota to manage; the constraint is the session's own budget.
- Only use when the user has asked for it. The point of this skill is usually a **different** pair
  of eyes, and a Claude subagent shares this session's blind spots. Opus/Sonnet reviewing
  Claude-written code are **not independent** — weight and label accordingly.
- **Give each subagent a SELF-CONTAINED prompt.** Embed the shared `_context.md` text AND that
  slice's brief verbatim; name the exact frozen checkout path + commit to read from; tell it to
  **write its own report** to the canonical `out/<slice>.<tag>.md` and reply with only the path +
  `TOTAL FINDINGS` + top finding. Do NOT tell it to read the briefs out of `docs/` — the context
  forbids reading `docs/`, and it will wander into other reviews' outputs. Embed instead.
- **`model:` picks the family; `effort:` sets the effort.** [fact 2026-10-09] The `Agent` tool takes
  `effort` (low, medium, high, xhigh, max): pass it when the user names a level. (Older notes said
  there was no effort setting; that is no longer true.) Record the effort you really set. A
  subagent runs on the session's machine; for a run on the laptop use
  `claude -p --model <id> --effort high` there.
- **Fan out in waves (~8 concurrent), backfill one as each finishes** — not all N at once. Track
  completion by listing the `out/` files, not only by notifications.

---

## Provider notes — read before the first dispatch

Moved here 2026-10-25 from the bodies of sliced-review, multi-fix and multi-build (they were the
same text three times). Exact model versions live in `models.md`; this section is wiring, routes
and traps.

**Swift builds: Sol goes through OpenCode, not Codex** (the user, 2026-09-30). In the `fix` modes, when Sol must build,
edit and test, or run any Swift (`swift build`, `swift test`, `swift run`, `xcodebuild`) — as a
builder, a fixer, or a checker that runs the tests — dispatch it with
`$RUNNERS_DIR/opencode/oc-run.sh --sol --write "$(cat brief)" < /dev/null` (= `openai/gpt-6.2-sol`,
variant high, the user's ChatGPT plan through OpenCode's OAuth login). `codex exec` CANNOT build Swift:
its sandbox nests `sandbox-exec` and blocks the `~/Library` caches and the network. A read-only
review that runs no Swift stays on `codex exec`. OpenCode-Sol and Codex-Sol are the SAME model:
never a fix and its cross-check, never two reviewers in one scorecard. Luna has no OpenCode
route, so Luna never builds Swift. Verified 2026-09-30: `swift build` + a ProKitTests lane, exit 0.

**Cursor carries two more models as of 2026-09-14** (the user widened its allowlist):
`cursor-run.sh --gemini` (Gemini Flash, collision-free) and `--muse` (Muse Spark — same model as
OpenCode Go `--muse`). Neither is in the default rings. They bill the SAME Cursor pool as Grok and
Composer, so no Cursor model checks another Cursor model's work, and no two Cursor arms run at once.
Sol and Opus stay refused on Cursor.

**GPT-6 Luna is an opt-in Codex arm at xhigh** (the user, 2026-09-22 — it replaces Cursor's GPT-5.6
Luna, which this skill no longer uses): `codex exec --skip-git-repo-check -m gpt-6-luna -c
model_reasoning_effort="xhigh" -s read-only -o "$T" … < /dev/null`. Not in the default rings. It bills
the SAME Codex pool as Sol, so Luna and Sol never check each other's work. Terra is not used.

**OpenCode Go is available as a substitute arm** (wired 2026-09-12; it was not a backend here
before). `$RUNNERS_DIR/opencode/oc-run.sh` with short flags: eleven short flags: `--qwen` (Qwen3.7 Plus),
`--qwen-max` (Qwen 3.8 Max), `--qwen-flash`, `--glm`, `--glm-std`, `--deepseek`,
`--deepseek-pro`, `--minimax`, `--muse`, all verified 2026-09-12, plus `--mimo-flash` (MiMo v2.6 Flash, added 2026-10-03, NOT probed). `--mimo` (MiMo v2.5 Pro) is BANNED and refused. It is NOT in the default rings; it is what you swap in when a named plan is exhausted or the user asks for it.

**Only `--qwen` and `--qwen-max` are collision-free.** `--qwen-flash`, `--glm`, `--deepseek` and
`--mimo-flash` are the same models as their Command Code, Cline and Devin copies (see
`models.md`), `--glm-std` is plain GLM 5.3, `--deepseek-pro` IS `cmd-deepseek-pro`,
and `--minimax` IS `cmd-minimax`. A different invoice is not a different pair of eyes, so none of
those may be a fix and its cross-check, and none may count twice in one scorecard. Traps:
`~/.claude/skills/sliced-review/references/runners.md` → "OpenCode Go".

**Free OpenCode arms (verified 2026-10-17, $0, free for now)** — short flags in `oc-run.sh` AND `pi-run.sh`: `--beam`, `--nemotron-vl`, `--deepseek-free`, `--glm-free`, `--minimax-3.1-free` (Pi hands these to oc-run.sh: the free tier answers only the OpenCode app). Long form `oc-run.sh --model opencode/<id>`
(provider `opencode/`, NOT `opencode-go/`; costs no Go credits): `beam-free` (Beam — new, lab
unknown, collision-free), `nemotron-3.5-super-vl-free` (Nemotron 3.5 Super VL, collision-free),
`minimax-m3.1-flash-free` (MiniMax M3.1 Flash, added 2026-10-19, collision-free: NOT the same
model as `--minimax` / `cmd-minimax` = MiniMax M3, but the same lab, so never use it to check an M3 fix),
`deepseek-v4.1-flash-free` (= OC `--deepseek` — same model), `glm-5.3-flash-free`
(= OC `--glm` — same model). Use them as extra free reviewers or helpers, ONE per
part. The DeepSeek and GLM free ids are the SAME eyes as their paid twins: never a fix and its
cross-check. Free pools may log prompts: never on client, NDA or credential-bearing repos.

**Pi is the MAIN harness; OpenCode is BACKUP ONLY** (the user, 2026-10-16). Run every OpenCode Go / Luna job with `$RUNNERS_DIR/pi/pi-run.sh`
takes the SAME short flags as `oc-run.sh` (`--qwen`, `--qwen-max`, `--qwen-flash`, `--glm`,
`--glm-std`, `--deepseek`, `--deepseek-pro`, `--minimax`, `--muse`, `--mimo-flash`) and bills the SAME
OpenCode Go key. Swap `oc-run.sh` → `pi-run.sh`, nothing else. Measured 2026-10-16 on DeepSeek V4.1
Flash (same task, 2 runs each): fix 53k vs 161k tokens, build 70k vs 212k, review 58k vs 64k —
about **3× fewer tokens** and ~3× lower API cost on fix/build, same results. Pi's system prompt is
~10k tokens vs OpenCode's ~30k, re-sent each turn. Read-only = tool allowlist `read,grep,find,ls`;
`--write` gives bash/edit/write. stderr prints `pi-run: usage: …`; log `$RUNNERS_DIR/pi/usage.jsonl`.
Same-model traps above still hold: `pi-run --deepseek` and `oc-run --deepseek` are ONE model.
Use `oc-run.sh` ONLY when (a) Pi fails (non-zero exit, empty answer, or `turns=0` in the usage line) — rerun the SAME task with the SAME flags on `oc-run.sh` and say so in the report — or (b) the job needs `--sol` (Pi has no Sol route). Luna: `pi-run.sh --model openai/gpt-5.6-luna --thinking xhigh`. Pi logs `secs` like oc-run (5 Luna review slices: Pi ~44 min vs OC 29 min, but 29 vs 24 bugs). Report:
`~/Desktop/Claude/docs/pi-vs-opencode/REPORT.md`.

**MiMo rule (the user, 2026-10-03): the only MiMo model is MiMo v2.6 Flash.** Never MiMo v2.5 or v2.5 Pro (and no
v2.6 Pro), on any route: Cline, OpenCode Go, Command Code. Use `cline-run.sh --mimo-flash` (works on
the Mac and on the laptop). Every runner refuses any other MiMo id (exit 2). If the asked model cannot run, STOP and
say so; never swap in another model version.

**Cline (ClinePass + Cline free models) is available as a substitute arm** (wired 2026-09-26,
The user's ClinePass, $9.99/mo). `$RUNNERS_DIR/cline/cline-run.sh` (the `cline` npm CLI, OAuth login in
`~/.cline`) with 14 ClinePass flags: `--mimo-flash` (MiMo v2.6 Flash, the default since 2026-10-03; `--mimo-pro`,
`--mimo25-pro` and `--mimo25` are BANNED and refused), `--deepseek-pro`, `--deepseek` (V4.1 Flash), `--glm`, `--glm-flash`,
`--minimax`, `--muse`, `--qwen-max` (3.8 Max), `--qwen37-max`, `--qwen-plus`; and 8
$0 free flags: `--free-bunny` (stealth), `--free-ultra`, `--free-super` (Nemotron 3), `--free-laguna`,
`--free-laguna-xs`, `--free-north`, `--free-dots`, `--free-router`. All 22 verified 2026-09-26 on a
read AND a write probe. It is NOT in the default rings. Quota IS
measurable: `QUOTA_PCT_CMD='$RUNNERS_DIR/cline/cline-quota.py --pct'` (worst of 5h/7d/30d caps).

**No ClinePass id is collision-free** — all 14 are the same weights as an OC Go, Command Code,
or Devin arm; Cline moves the BILL, not the eyes. The only arms that are new eyes
are the free `--free-laguna`, `--free-super` and `--free-dots` (`--free-ultra` / `--free-north` ARE
OpenCode free's; `--free-bunny` and `--free-router` are unknown models — never use them as a
cross-check). Free models are shared OpenRouter pools: they 429 or 404 when busy, and they may log
prompts, so the user's OWN code only. Traps: `~/.claude/skills/sliced-review/references/runners.md` →
"Cline".

**xAI is available as a substitute arm** (wired 2026-09-16, the user's own xAI plan connected to
OpenCode by OAuth). `$RUNNERS_DIR/xai/xai-run.sh` with short flags: `--grok` (Grok, high, the
default), `--grok45` (Grok 4.5, high), `--grok43` (Grok 4.3, high), `--build` (grok-build-0.1) and
`--grok420` (grok-4.20 reasoning). All five verified 2026-09-16 on a planted bug. **Grok runs on Cursor or xAI:** `references/pick-provider.py --model Grok` picks the one whose
tokens expire first. One Grok per run, never a second Grok beside it.

**Every xAI arm is Grok, so none is independent of the core three's Grok.** `--grok` IS Cursor's
`grok-4.7-high`, `--grok45` IS `cmd-grok`, and `--grok43` / `--build` / `--grok420` are the
same model family. No xAI arm may cross-check or review a Cursor Grok arm's work, and no xAI arm
counts as a separate reviewer beside a Cursor Grok arm in one scorecard. Quota: `codexbar usage
--provider grok`. Traps: `~/.claude/skills/sliced-review/references/runners.md` → "xAI".

**Devin is available as an extra arm** (wired 2026-10-06, the user's Devin Pro plan).
`$RUNNERS_DIR/devin/devin-run.sh` with short flags: `--swe2` (SWE high, the default, listed Free),
`--sol` (GPT-6.1 Sol medium), `--luna` (GPT-6 Luna medium), `--glm` (GLM 5.3 Flash max),
`--deepseek` (DeepSeek V4.1 Flash high) and `--fusion` (GPT-6.1 Sol high leads, SWE-2 medium does
the hands-on work, ONE run), plus `--swe17` (SWE-1.7 Max) and `--glm52` (GLM-5.2 High), both free per
Devin's docs. `--effort <level>` changes the effort. All verified 2026-10-06. SWE is free only
through 2026-10-15. Keep Sol / Luna requests under 272K tokens (double price above it). It is NOT in the default rings; use it only when the user names it. **Only `--swe2` is new
eyes.** `--sol` and `--fusion` ARE Sol, `--luna` IS Codex Luna, `--glm` IS GLM Flash (OC, Command Code, Cline),
`--deepseek` IS OpenCode Go's `--deepseek`: none may cross-check, review, or count beside the same
model on its pinned route. Fusion pair is fixed (the user): lead Sol, sidekick SWE. The runner
refuses every id outside this roster (Fable always). Exit code is 0 even on a rejected tool or an
empty answer, so judge by the result line. Telemetry ON: the user's OWN code only. It reports NO quota;
tokens and an estimated cost are logged per run (`$RUNNERS_DIR/devin/devin-usage.py --week`). Traps: `~/.claude/skills/sliced-review/references/runners.md` → "Devin".

## Orchestration gotchas — background jobs, worktrees, output paths

These bit real runs. They apply to this skill and to multi-build / multi-fix.

- **Never launch a long job with `nohup … &` inside a tool shell.** The trailing `&` makes the
  shell return immediately, so you get **no completion notification**, AND the detached child can be
  **killed when the tool shell ends**. Use the harness's tracked background instead (run the command
  directly with `run_in_background`, no `nohup`, no `&`): it is tracked, survives across turns, and
  fires a completion notification. Long integrators/aggregators are resumable, so if you already
  launched one wrong, stop it and relaunch it tracked — no work is lost. Poll a log file only as a
  fallback, never as the primary signal.
- **Read at the peers' commit.** A reviewer arm must read the code at the **same commit** as the
  runs it will be scored against; a model *completing* a partial run must use the commit its earlier
  slices used (not "latest"). Check per-run `review_commit` before you start. Make a **dedicated
  read-only worktree** at that commit (`git worktree add --detach <path> <commit>`); never
  `stash`/`prune` or reuse someone else's worktree, and remove your own at wrap.
- **Write outputs into the canonical, synced results dir.** A job that writes to a home-dir cache or
  anywhere outside the synced tree won't reach the session that launched it (and won't reach the
  user's other machine). Copy such outputs into the results dir explicitly.

---

## Gotchas that keep biting — per backend

Every line here was learned the hard way. Skim the ones for the arm you're about to run.

**Universal**
- **`< /dev/null` on EVERY `codex exec` / `opencode run` / `oc-run.sh` call**, and
  put it in the *subagent's* brief too — without it they hang after init reading stdin, and a
  subagent leaves GHOST TASKS that show "active, 0 bytes" for hours after the process is dead.
- **Never judge a run by log size or `pgrep`.** `claude -p` backends (GLM) buffer to the end;
  `pgrep -f` self-matches your own polling shell. Judge by: process gone AND log > its banner floor,
  or (better) by the run's own result line + owned-file mtimes + moving quota.
- **Quota/error detection scans only the LAST ~15–20 lines**, never the whole report — reviewers
  wander into code/docs containing `429`, `quota`, `rate limit` and trip a false quota-out.
- **A blocked write hangs a background subagent forever** (no one answers its permission prompt). A
  trailing `tool_use` with no `tool_result` = this. Wire anything it must write BEFORE dispatch and
  tell it never to touch frozen files.

**Codex / Sol / Astra**
- Two `codex` binaries: `$RUNNERS_DIR/node/bin/codex` (npm) and `~/.local/bin/codex` (standalone,
  `codex update`). Both 0.156.0 on 2026-09-22. Since that update the installer's block in
  `~/.zprofile` puts `~/.local/bin` FIRST in new terminals — keep the two on the same version. A **400 "requires a newer version of Codex"** = old
  CLI, not "no access"; a *"is not supported"* = wrong id. Upgrade the one that wins PATH.
- Sol house default is **GPT-6.2 Sol at high (GPT-6.1 Sol until 2026-11-19)** (was GPT-6 Sol high until 2026-09-30, GPT-5.6 Sol xhigh until 2026-09-22; GPT-6.1 Sol smoke-tested OK on Codex CLI 0.159.2, 2026-09-30); pass
  `-m gpt-6.2-sol -c model_reasoning_effort="high"` explicitly in anything recorded. GPT-6 Luna runs at
  **xhigh**. GPT-6.2 Sol and Luna need Codex CLI **≥ 0.156** — on 0.153/0.154 they fail with a 400
  *"not supported when using Codex with a ChatGPT account"* (that one is the OLD CLI, not the plan). Sol = read-only reviewer; `-s workspace-write` **blocks localhost** (DB tests die) and
  cannot build a Swift package — never make Codex a builder there.
- `codex:codex-rescue` subagent is **BANNED** (overwrote committed work).

**Cursor (Grok 4.7 / Composer / Gemini / Muse / Luna)**
- One shared quota pool → **no two Cursor arms at once**, and a Cursor arm never checks another
  Cursor arm. A `--write` build can exit 1 at the end and **lose its whole report** — tell it to
  WRITE the report to a worktree file before printing.

**Command Code**
- `cmd` self-updates unless `--no-auto-update`. 5-hour usage limit hits mid-run → fast SKIPs.
- **qwen3.8-27b**: no `high` effort (low/medium/xhigh only); needs **`--tools-all`** in headless
  `-p` or it returns an "I'll read the files" stub; still ~40% stub → retry up to 6× per slice,
  break on `TOTAL FINDINGS`. `-p` prints no token usage (cost not recorded).

**OpenCode Go**
- Plan-mode AUTO-REJECTS reads/writes **outside the cwd** (`external_directory`) and ends exit 0
  with no verdict → copy briefs/diffs INTO the worktree; brief says "read only inside <worktree>".
- Weekly allowance: no `--variant high`, no retry loops. `--deepseek` here == Cline / Command Code /
  Devin `--deepseek` (same model) — never pair them as fix+check.

**Claude subagents (Opus / Sonnet)** — see the section above; and a background Opus subagent will
stop while its own suite runs in the background — tell it to run tests in the foreground.

## Linux laptop (the second box)

The triage/review harness usually runs here. Extra traps:
- **Codex sandbox needs bubblewrap + unprivileged user namespaces**, blocked by AppArmor on Ubuntu
  24.04 → every sandboxed read fails `bwrap: ... Operation not permitted` and the model reports
  BLOCKED (looks like a bad review). Fix persisted in `/etc/sysctl.d/60-codex-bwrap.conf`:
  `kernel.apparmor_restrict_unprivileged_userns = 0`. Mac is unaffected.
- The Mac has **no `timeout(1)`/`gtimeout`** — if you run the harness on the Mac instead, it needs
  the `~/.local/bin/timeout` perl shim (triage.py calls `timeout SECS cmd`).
- The laptop has its **own** xAI device-code login (never copy the OAuth token). Its
  `~/.claude/skills` git pull fails (no GitHub auth) and it carries dirty entries — don't expect it
  to be in sync; push from the Mac and pull manually.
- Stop Syncthing before moving any profile dirs on the laptop.

## Wiring a backend that is not listed

Answer the four questions, then write `runner.env`. Nothing else in the kit changes — that is the
whole point of keeping the backend in one file.

If the new backend has a quota endpoint, write a one-line adapter that prints **a single integer
0–100 = percent already used**. The runner needs nothing else from it.

Add what you learn to [`../FIELD-NOTES.md`](../FIELD-NOTES.md), especially the exact out-of-quota
wording — the next session greps for it.

## Pi (pi.dev) — default driver for OpenCode Go models (2026-10-16)

**Pi is the MAIN harness; OpenCode is BACKUP ONLY** (the user, 2026-10-16). Run every OpenCode Go / Luna job with `$RUNNERS_DIR/pi/pi-run.sh`
takes the SAME short flags as `oc-run.sh` (`--qwen`, `--qwen-max`, `--qwen-flash`, `--glm`,
`--glm-std`, `--deepseek`, `--deepseek-pro`, `--minimax`, `--muse`, `--mimo-flash`) and bills the SAME
OpenCode Go key. Swap `oc-run.sh` → `pi-run.sh`, nothing else. Measured 2026-10-16 on DeepSeek V4.1
Flash (same task, 2 runs each): fix 53k vs 161k tokens, build 70k vs 212k, review 58k vs 64k —
about **3× fewer tokens** and ~3× lower API cost on fix/build, same results. Pi's system prompt is
~10k tokens vs OpenCode's ~30k, re-sent each turn. Read-only = tool allowlist `read,grep,find,ls`;
`--write` gives bash/edit/write. stderr prints `pi-run: usage: …`; log `$RUNNERS_DIR/pi/usage.jsonl`.
Same-model traps above still hold: `pi-run --deepseek` and `oc-run --deepseek` are ONE model.
Use `oc-run.sh` ONLY when (a) Pi fails (non-zero exit, empty answer, or `turns=0` in the usage line) — rerun the SAME task with the SAME flags on `oc-run.sh` and say so in the report — or (b) the job needs `--sol` (Pi has no Sol route). Luna: `pi-run.sh --model openai/gpt-5.6-luna --thinking xhigh`. Pi logs `secs` like oc-run (5 Luna review slices: Pi ~44 min vs OC 29 min, but 29 vs 24 bugs). Report:
`~/Desktop/Claude/docs/pi-vs-opencode/REPORT.md`.

**Other plans in Pi** (2026-10-16): (Cesego and Xiaomi removed 2026-10-25.) Pi auto-falls back to `oc-run.sh` on failure (`PI_NO_FALLBACK=1` stops it). Full numbers: `docs/pi-vs-opencode/REPORT.md` in this repo.

**Removed plans** (z.ai, Nexum, Xiaomi; Cesego and Kimi): not in use. Their old setup notes are
kept outside the skill flow in `../archive/removed-providers.md`; open it only when the user asks to
bring one back.

**Plans checked for Pi (2026-10-16):**
- **OpenCode Go**: CONNECTED (Pi default, `OPENCODE_API_KEY` from OpenCode auth).
- **Cursor, Devin**: NOT possible. They have no model API; they run only through their own CLIs (`cursor-run.sh`, `devin-run.sh`).
- **Command Code**: NOT possible today. No OpenAI-style route on api.commandcode.ai (404 on `/v1/models`, `/v1/chat/completions`); stay on `cmd-run.sh`.
- **Cline**: maybe. `api.cline.bot/api/v1/models` answers with the CLI OAuth token, but chat gave 401 (needs a fresh Cline login, and there was no usage left on 10-16). To try: custom `models.json` provider `cline`, `baseUrl https://api.cline.bot/api/v1`, `api openai-completions`, `apiKey "!jq -r .providers.cline.settings.auth.accessToken ~/.cline/data/settings/providers.json"`.
- **xAI**: maybe. The OpenCode OAuth token was refused by api.x.ai (403), and there was no usage left on 10-16. Pi built-in `xai` needs an `XAI_API_KEY` (console.x.ai). A 4xx in the error means an account problem, not Pi.