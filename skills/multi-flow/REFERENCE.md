# Multi Flow — Reference

Consulted on demand by [`SKILL.md`](SKILL.md).

## State file template

Write to `.multiflow/STATE.md` at Phase 0. Keep it short — a fresh agent must read it in seconds.

```markdown
# MULTI FLOW — <project name>

branch:  <working branch>
tracker: github | linear | local (.scratch/<slug>/issues/)
layout:  <path of the agreed multi-plan layout>
spec:    <path or issue ref>
tickets: <path glob or issue query>

## PHASES
- [ ] 0 preflight
- [ ] 1 interview     grill-with-docs
- [ ] 2 plan          multi-plan 3      + wrap lite
- [ ] 3 spec          to-spec
- [ ] 4 tickets       to-tickets
- [ ] 5 build         multi-build 3     + wrap lite per run
- [ ] 6 review        sliced-review 3   + wrap lite
- [ ] 7 fix           multi-fix 3       + wrap lite
- [ ] 8 close         wrap (full)

## TICKETS
| # | title | blocked by | status | commit |
|---|-------|-----------|--------|--------|
| 1 | ...   | none      | [ ]    |        |

## RULES (never break)
- <constraints agreed in Phase 1/2 that a fresh agent would not infer>

## GOTCHAS
- <one line each, learned during the run>
```

`RULES` and `GOTCHAS` are the only things worth carrying out of a dead context. Keep both terse.

## Triage bands (Phase 7)

| Band | Definition |
|---|---|
| **HIGH** | Can lose data, expose a secret, let an unauthorised actor through, take the app down, or corrupt state. Also: silently wrong in a path the user cannot see. |
| **MEDIUM** | Wrong behaviour in a real path, with a workaround or visible symptom. Missing test on a HIGH-risk seam. Performance bad enough to be a bug. |
| **LOW** | Style, naming, duplication, dead code. No behaviour changes if never fixed. |

Band by worst plausible consequence, not by how hard the fix looks. Two models agreeing raises
confidence, never the band. One model alone finding a HIGH is still HIGH until you disprove it.
(`sliced-review` already triages with three judges — use its bands as the start, then apply your own read.)

## Where the pieces live

| Piece | Path |
|---|---|
| Model list (the ONE place) | `~/.claude/skills/_shared/models.md` |
| Matt's skills (do not edit) | `~/.claude/skills/{grill-with-docs,to-spec,to-tickets}` → `~/.agents/skills/` |
| Our four | `~/.claude/skills/{multi-plan,multi-build,sliced-review,multi-fix}` |
| Run state | `.multiflow/` in the project |
