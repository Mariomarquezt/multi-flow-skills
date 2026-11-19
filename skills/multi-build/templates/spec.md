# Feature spec — <feature name> — <project> — <YYYY-MM-DD>

Mode: `<invocation>` · builders: <N> · status: <draft | seams agreed | building | shipped>

## Goal

<The user's words, one paragraph.>

<One sentence in the session model's words: what will be true when this is done.>

## Acceptance criteria

Each one is a test somebody could write. Given / when / then. Numbered; parts reference these.

1. **AC-1** — Given <state>, when <action>, then <observable result>.
2. **AC-2** — …

## Out of scope

- <thing this feature deliberately does not do>

## Constraints

- <public interface that must not change>
- <data that must not be migrated or lost>
- <behaviour an existing test pins>
- <performance budget, design system, convention>

## Open questions

- <question> — proposed answer: <answer>. (Resolved: <yes/no, when>)

Do not dispatch a builder while this list has an unresolved item.

## Seams — the contracts every part builds against

Written by the session model BEFORE any builder starts. Copied verbatim into every brief.

### S-1 — <name>

- **Owner:** part <P-n> · **Consumers:** parts <P-m, P-k>
- **Signature / shape:**
  ```
  <function signature with types, or table columns, or JSON fields, or route + payload>
  ```
- **On failure:** <what it returns / throws / emits>
- **Stub needed by consumers' tests:** <yes — owner ships it first | no>

### S-2 — …

Builders may PROPOSE a seam change. They may not make one silently.

## Parts — the split

| part | files (owned, exclusive) | criteria | builder | reviewer |
|---|---|---|---|---|
| P-1 | `<path>`, `<path>` | AC-1, AC-3 | <model> | <model> |
| P-2 | … | … | … | … |
| integration | — | AC-<n> | session model | <least-author model> |

Every criterion appears in exactly one row. Reviewer is never the builder, never the same
subscription, never Claude for Opus.

## Shipped — filled in at Step 9

| criterion | proven by test | part | notes |
|---|---|---|---|
| AC-1 | `<test file>::<name>` | P-1 | |

- **Scoped out during the build:** <what, why, where it is recorded>
- **Commit:** `<sha>`
