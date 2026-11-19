# Item {{ID}}: {{TITLE}}

The lead writes this file ONE time per item. The sub-task brief, the repro brief and the check
brief use it. Nobody edits it after the first dispatch (a change = a new line `CHANGED <date>: ...`
at the end, and the checker is told).

## Claim / wish (verbatim from the source)

{{TEXT, with the sequence of events it describes}}

## Done lines

- D1: {{what is true when this item is done, one fact per line, with the exact message or value}}
- D2: {{...}}

## Test list (one test per line)

- T1 refusal: {{case}} -> {{exact message / value}}
- T2 success: {{case}} -> {{value that comes back}} + {{side effects that must happen}}
- T3 failure side effects: {{case}} -> {{what must NOT run: audit, redirect, write}}
- T4 edge input: {{empty | array | null | over the limit}} -> {{result}}

(or one line: `NONE: type-only change` | `TEST-ONLY: the tests are the change; break: <...> -> <test> fails`)
(a proof that is a COMMAND RUN, not a test case: `T5 run: <command> -> <expected output>`; the lead
runs it in the gate and its output goes in the gate file, so that the checker sees it)

## Seam / contract (verbatim, if this item uses or makes a shared interface; else delete)

{{types, function signatures, exact messages}}

## Must not break

{{public contract, data, behaviour a test pins}}

## Map (from the scout; `scout says` = the lead did not open it)

{{path:from-to; function; callers; tests; throws; db}}
