# Changelog

The version lives in `SKILL.md` frontmatter (`version:`) and as a git tag. Compare yours with
`grep ^version ~/.claude/skills/sliced-review/SKILL.md` to see if you are behind.

## 2.2.0 — 2026-09-04

- **Review report, Markdown + HTML.** `templates/build-report.py` (stdlib only) renders
  `docs/reviews/report-<date>.md` and a self-contained `report-<date>.html` from `findings.json`,
  the scorecard and each lane's `ledger.tsv`: counts, the ranked scorecard, a lanes table
  (total time, avg per slice, slowest slice, slice status per model) and every finding grouped by
  severity with file, status, finder and verified flag.
- **`report` suffix** (`/sliced-review 5 report`, `fix fast 3 report no wrap`) builds it without
  asking. Without the suffix the skill asks once at the end of Step 12 (new §12b).

## 2.1.1 — 2026-09-04

- Scorecard: time is explicit per model — total time, average per slice, slowest slice (with its
  id), all from `ledger.tsv`. Time is shown beside the score but never changes the rank.

## 2.1.0 — 2026-09-04

- **Model scorecard.** Every multi-model run now ends Step 10 by writing
  `docs/reviews/scorecard-<date>.md` (template in `templates/scorecard.md`): one row per model
  with reported / verified / refuted counts, precision, verified findings by severity
  (critical · high · medium · low), unique finds, missed critical/high, a weighted score
  (8 · 4 · 2 · 1) and the ledger's wall clock and cost. Models are ranked by score; ties break by
  unique finds, then precision. Grades use findings that survived triage at the triager's
  severity, never raw claims or the model's own labels.
- New honesty rule: never rank models on raw counts or self-reported severity.

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
