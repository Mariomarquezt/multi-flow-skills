# Changelog

The version lives in `SKILL.md` frontmatter (`version:`) and as a git tag. Compare yours with
`grep ^version ~/.claude/skills/sliced-review/SKILL.md` to see if you are behind.

## 2.0.1 — 2026-09-04

(2.0.0 was published for a few minutes the same day and withdrawn; 2.0.1 is the release.)

Rebuilt around a measured five-model reviewer stack. Seven models ran the same five slices of a
~20k-line codebase head to head; the roster and effort levels below are what that produced.

- **Invocation modes** (new section at the top of `SKILL.md`, parsed before anything else):
  bare `/sliced-review` and `3` = core three (GPT-5.6 Sol xhigh, Grok 4.6 high, Opus 5 high);
  `5` adds GLM 5.3 Flash and Composer 2.5; `fast` = Composer alone.
- **`fix` modes** (§11g): `fix`, `fix 3`, `fix 5`, `fix high` also triage, apply fixes with the
  reviewing models, cross-check every fix with a DIFFERENT model, and commit.
- **`fix fast` modes** (§11h): same, pipelined — each slice's fixes start as soon as that slice's
  review lands, with a cap on concurrent Cursor consumers.
- **`no wrap` suffix** skips the closing wrap-up step.
- **Effort is pinned, never inherited.** Every runner takes an explicit `--effort`
  (`low|medium|high|xhigh|max`). Grok stays at `high`: xhigh returned half the findings and zero
  HIGHs.
- **Route pinning** in `references/runners.md`: one correct route per model; the Cursor wrapper
  hard-refuses anything but Grok and Composer. Codex runs require `-o/--output-last-message`.
- **Step 12 — record the findings.** Every review ends by writing `docs/reviews/findings.json`
  (schema in `templates/findings.json`) so findings survive past the `out/` folder.
- **FIELD-NOTES**: four-reviewer run on 42k lines; the "never ran on Cursor" claim retracted.

## 1.0.0 — 2026-08-22

Initial public release: blast-radius-ordered slices, cost ledger, activity-aware watchdog with a
hard wall-clock cap, quota guard, `chain.sh` queue runner, triple review with cross-reviewed
fixes and capped adversarial rounds.
