# multi-flow skills

A set of Claude Code skills that take a new project from idea to reviewed, fixed code, with several AI models checking each other's work.

| Skill | What it does |
|---|---|
| `multi-flow` | The main skill. Runs the whole path, phase by phase, and keeps its state in `.multiflow/STATE.md`. |
| `multi-plan` | One model drafts a plan. Other models attack it. The session model rules on every finding. |
| `multi-build` | Builds one feature with several models. Each part is checked by a different model. |
| `sliced-review` | Reviews a whole codebase in small slices with several models, then triages the findings. |
| `multi-fix` | Fixes a list of defects with several models. A different model checks each fix. |

`skills/_shared/models.md` is the ONE file that names model versions. To move to a new model version, edit that file (and the model id in `sliced-review/references/runners.md`).

## The flow

```
grill-with-docs -> multi-plan -> to-spec -> to-tickets -> multi-build -> sliced-review -> multi-fix -> wrap
   (Matt)           (ours)       (Matt)      (Matt)         (ours)         (ours)         (ours)
```

`/wrap lite` runs after each of our skills.

## Install

1. Install the Matt Pocock skills that `multi-flow` calls. We do **not** copy them, so you always get his latest version. Repo: https://github.com/mattpocock/skills (MIT).

   **Only the ones you need** (six skills):
   ```bash
   npx skills add mattpocock/skills --skill grill-with-docs grilling domain-modeling to-spec to-tickets setup-matt-pocock-skills
   ```
   `grill-with-docs` runs `grilling` and `domain-modeling` inside it. `setup-matt-pocock-skills` sets up your issue tracker (needed before `to-spec` and `to-tickets`).

   **Or his whole set:**
   ```bash
   npx skills add mattpocock/skills
   ```
   To list what is in his repo first, add `--list`. To update later: `npx skills update`.
2. Copy the folders in `skills/` into `~/.claude/skills/`. Keep the folder names. The skills point to each other under that path.
3. Provide a `wrap` skill. `multi-flow` and the four skills call `/wrap lite` at the end. Use your own, or pass `no wrap`.
4. Start a new project with `/multi-flow`.

## Models and runners (read this)

The skills hand work to other models through small wrapper scripts, for example `oc-run.sh` (OpenCode), `cursor-run.sh`, `cline-run.sh`, `pi-run.sh`, `xai-run.sh`, `cmd-run.sh`. **These scripts are not included.** The skills call them as `$RUNNERS_DIR/<tool>/<script>`.

- Set `RUNNERS_DIR` to the folder that holds your wrappers.
- `skills/sliced-review/references/runners.md` describes what each wrapper must do (prompt in, report on stdout, read-only unless told otherwise).
- You do not need every provider. Edit `skills/_shared/models.md` so it lists only the providers you have. Fewer providers means a smaller mode (`2` or `3` instead of `5` or `8`).
- Codex runs need Codex CLI 0.170 or newer for the 6.2 models.

## Owner rules baked in

`_shared/models.md` and `multi-plan` contain the author's own rules (for example "never use Fable", "no OpenRouter unless approved"). Change them to fit you.

## Credit

`grill-with-docs`, `grilling`, `domain-modeling`, `to-spec`, `to-tickets` and `setup-matt-pocock-skills` are by Matt Pocock (https://github.com/mattpocock/skills). They are not part of this repo.
