# Models — the ONE place that names model versions and providers

sliced-review, multi-fix (multi-model-fix) and multi-build call every model by a **short name**.
This file says which exact model each short name means today, and which subscriptions can run it.
Read it before the first dispatch. Reports, ledgers and scorecards write the exact model id and the
provider that ran it, so old runs stay comparable.

**To move a model to a new version:** change its row here, then the same id in the runner command
(`runners.md`). The SKILL.md files only use the short name.

**Pick a model by its row, never by "latest" or "newest".** The newest Claude model is a Fable
model, and Fable is banned.

## Main roster

| short name | exact model today | model id | providers (codexbar key) | effort |
|---|---|---|---|---|
| **Opus** | Opus 5.5 | `claude-opus-5-5` | `claude` — Claude subscription, `Agent` subagent, omit `model` | high |
| **Sol** | GPT-6.2 Sol | `gpt-6.2-sol` | `codex` | high |
| **Grok** | Grok 4.6 | `cursor-grok-4.6-high` (Cursor), `grok-4.6` (xAI) | `cursor`, `xai` | high |
| **Grok (fix, build)** | Grok 4.7 | `grok-4.7-high` (Cursor), `grok-4.7` (xAI) | `cursor`, `xai` | high |
| **DeepSeek Flash** | DeepSeek V4.1 Flash | `deepseek-v4.1-flash` | `opencodego`, `cmd`, `cline`, `devin` | high |
| **GLM Flash** | GLM 5.3 Flash | `glm-5.3-flash` | `opencodego`, `cmd`, `cline`, `devin` | max |
| **MiMo Flash** | MiMo v2.6 Flash | `mimo-v2.6-flash` | `opencodego`, `cmd`, `cline` | high |
| **Qwen Flash** | Qwen 3.8 Flash | `qwen3.8-flash` | `opencodego`, `cmd` | high |
| **MiniMax Flash** | MiniMax M3.1 Flash | `minimax-m3.1-flash` | `opencodego` (paid Go plan; the free `minimax-m3.1-flash-free` was gone on 2026-10-25) | default |
| **Astra** (extra lane, no mode yet, added 2026-11-19) | GPT-6.2 Astra | `gpt-6.2-astra` | `codex` | high |

**Grok has two rows (the user, 2026-10-25).** sliced-review lanes and judges, and every other
review, use **Grok** = Grok 4.6: on the Nova Gate test it matched Grok 4.7 (score 25 vs 24,
precision 0.64 vs 0.57) in 45 % of the time. multi-fix and multi-build (fixers, builders and their
checks) use **Grok (fix, build)** = Grok 4.7 until the user moves them.

Mode `5` uses the first five rows (Grok = the 4.6 row). Mode `8` (sliced-review only, added 2026-10-25) uses all eight.
MiniMax Flash joined on the 22-project scorecard (2026-10-25): 1,557 confirmed findings, 250
critical/high, precision 0.82, and 4 of the 6 late critical/high bugs (measured on the free route,
same model).
MiMo Flash and Qwen Flash are also cheaper triage judges (Step 10).

## Cheaper triage and extra lanes

| short name | exact model today | model id | providers (codexbar key) | effort |
|---|---|---|---|---|
| **Luna** | GPT-6 Luna | `gpt-6-luna` | `codex` | xhigh |
| **Composer** | Composer 2.5 | `composer-2.5` | `cursor` | — |
| **SWE** | Devin SWE-2 | `swe-2` | `devin` (paid: ask the user first) | — |
| **Haiku** | Haiku 5.5 | `claude-haiku-5-5` | `claude` — ONLY the live-report monitor (the user's choice, 2026-10-25); never a reviewer, fixer or judge | — |

## Antigravity — Gemini lanes (added 2026-11-17, the user)

Google's Gemini models on the user's **Google AI Ultra** plan, through the Antigravity CLI (`agy`).
**Gemini only** (the user, 2026-11-17): the runner refuses Antigravity's Claude and GPT-OSS models.
They are extra lanes and swap-ins for now: no mode (`3`, `5`, `8`) uses them until the user moves
them into a mode. Review quality on real code is NOT measured yet: one planted two-bug file only.

| short name | exact model today | model id | providers (codexbar key) | effort |
|---|---|---|---|---|
| **Gemini Hydrogen** | Gemini 4 Hydrogen | `gemini-4-hydrogen-high` | `antigravity` | high (low..xhigh) |
| **Gemini Carbon** | Gemini 4 Carbon | `gemini-4-carbon-high` | `antigravity` | high |
| **Gemini Argon** | Gemini 4 Argon | `gemini-4-argon-high` | `antigravity` | high |
| **Gemini Flash** | Gemini 3.8 Flash | `gemini-3.8-flash-high` | `antigravity`, `cursor` | high |

Call: `$RUNNERS_DIR/antigravity/agy-run.sh --hydrogen | --carbon | --argon | --flash "<prompt>"`
(read-only by default; `--write` for a fixer or builder). Cursor's Gemini Flash: `cursor-run.sh --gemini`.
All four are Gemini: a Gemini lane never cross-checks another Gemini lane's work, and Gemini Flash on
Antigravity and on Cursor is ONE model (one pair of eyes).
Not used: `gemini-pro-orchestrator*` (they run sub-agents, not one review).

## Free stealth lanes (added 2026-11-05, the user)

Extra review lanes that cost $0. Use them in any mode, on top of the mode's roster. They are
**stealth** models: the lab is not named, so they may be the same eyes as a roster model. Never use
one as the only check on a fix, and never count it as a separate model in a scorecard until a
test shows it finds different bugs. Free pools may log prompts: skip them on client, NDA or
credential-bearing repos.

| short name | model id | provider (slot key) | lane | runner |
|---|---|---|---|---|
| **Crouton** | `stealth/crouton-alpha` (1M context) | OpenRouter free + OpenCode free (`orfree` = total cap) | `crouton` | `~/work/sr-kits/crouton-route.sh` |
| **Pulse** | `opencode/pulse-alpha-free` | OpenCode free tier (`ocpulse` slot key, own cap) | `pulse` | `$RUNNERS_DIR/opencode/oc-run.sh --model opencode/pulse-alpha-free` |

`or-free-run.sh` checks OpenRouter's public price list before every run and refuses (exit 3) any
model whose price is not exactly $0.

**Crouton routes (checked 2026-11-05).** The `crouton` lane runs `templates/crouton-route.sh`, which
spreads the lane over every free route that works, with a cap per route (`crouton-routes.conf`) and a
10-minute cooldown on a route that answers 429:
- works: OpenRouter free (`or-free-run.sh --crouton`), OpenCode free (`opencode/crouton-alpha-free`);
- listed but refused: Cline catalog lists `stealth/crouton-alpha` but a run says "model not found";
  Command Code lists it on some accounts only ("unknown model" on the laptop account, CLI 1.88.3).
Pulse exists only on the OpenCode free tier.
Kalmia, Kerria, Kentia, Mura: in none of the subscriptions (OpenRouter, OpenCode, Cursor, Devin,
Command Code, Cline, xAI, Codex) on 2026-11-05.

## Which provider runs the model — use the tokens that expire first

When a model has more than one provider, run:

```bash
python3 ~/.claude/skills/sliced-review/references/pick-provider.py --model "Grok"
```

It reads this file's provider list, asks codexbar (and the Command Code and Cline quota scripts) for
each subscription's weekly and monthly windows, and picks the provider whose window **resets
soonest while it still has the most tokens left** (score = % left ÷ hours to reset). A provider with
any window at 95% used or more is skipped. Without `--model` it prints the whole table. Run it again
before each new wave of slices: the best provider changes as windows reset.

How to call each model on the provider the picker chose (read-only; add `--write` only for a fixer):

| model | `opencodego` (Pi) | `cmd` | `cline` | `devin` |
|---|---|---|---|---|
| DeepSeek Flash | `pi-run.sh --deepseek` | `cmd-run.sh --model deepseek-v4.1-flash` | `cline-run.sh --deepseek` | `devin-run.sh --deepseek` |
| GLM Flash | `pi-run.sh --glm` | `cmd-run.sh --model glm-5.3-flash` | `cline-run.sh --glm-flash` | `devin-run.sh --glm` |
| Qwen Flash | `pi-run.sh --qwen-flash` | `cmd-run.sh --model qwen3.8-flash` | — | — |
| MiMo Flash | `pi-run.sh --mimo-flash` | `cmd-run.sh --model mimo-v2.6-flash` | `cline-run.sh --mimo-flash` | — |

MiniMax Flash (`opencodego`): `oc-run.sh --model opencode-go/minimax-m3.1-flash` (tested 2026-10-25).
Not `--minimax`: that is MiniMax M3, a different model. Also on OpenRouter (ask the user first).

Grok (reviews): `cursor-run.sh --model cursor-grok-4.6-high` (`cursor`) or `xai-run.sh --grok46` (`xai`).
Grok (fix, build): `cursor-run.sh --model grok-4.7-high` (`cursor`) or `xai-run.sh --grok` (`xai`).
Cursor Grok lanes always run inside `hb.sh`.

Write the chosen provider in `runner.env` and in the ledger. Two providers of ONE model are still one
pair of eyes: never use them as a fix and its cross-check, or as two reviewers in one scorecard.

| codexbar key | subscription | quota source | runner (flags in `runners.md`) |
|---|---|---|---|
| `claude` | Claude | `codexbar usage --provider claude` | `Agent` subagent |
| `codex` | Codex | `codexbar usage --provider codex` | `codex exec` |
| `cursor` | Cursor | `codexbar usage --provider cursor` | `$RUNNERS_DIR/cursor/cursor-run.sh` |
| `xai` | xAI (SuperGrok) | `codexbar usage --provider grok` | `$RUNNERS_DIR/xai/xai-run.sh` |
| `opencodego` | OpenCode Go | `codexbar usage --provider opencodego` | `$RUNNERS_DIR/pi/pi-run.sh` (backup `oc-run.sh`) |
| `cmd` | Command Code | `$RUNNERS_DIR/cmd/cmd-pool.py status` | `$RUNNERS_DIR/cmd/cmd-run.sh` |
| `cline` | ClinePass | `$RUNNERS_DIR/cline/cline-quota.py --pct` (rolling, no reset time) | `$RUNNERS_DIR/cline/cline-run.sh` |
| `devin` | Devin | `codexbar usage --provider devin` | `$RUNNERS_DIR/devin/devin-run.sh` |
| `antigravity` | Google AI Ultra (Antigravity CLI) | `codexbar usage --provider antigravity` (5-hour + weekly Gemini windows) | `$RUNNERS_DIR/antigravity/agy-run.sh` |
| `ocfree` | OpenCode free tier ($0) | none (no quota window; it can 429 or vanish) | `$RUNNERS_DIR/opencode/oc-run.sh` |

## Banned — never use, on any route

- **Fable** (any version) and **Opus 5 or older**.
- **MiMo v2.5** and **MiMo v2.5 Pro**.
- **Removed providers** (the user, 2026-10-25): Cesego, Kimi, Nexum, Xiaomi MiMo Token Plan.
- **Antigravity's non-Gemini models** (the user, 2026-11-17): `claude-opus-4-6-thinking`,
  `claude-sonnet-4-6`, `gpt-oss-120b-medium`. The runner refuses them.
- **OpenRouter**, unless the user approves that one task. Exception (the user, 2026-11-05): FREE
  OpenRouter models through `or-free-run.sh` (price guard), today Crouton Alpha.

A ban names the exact thing it bans, so this list keeps exact versions.
