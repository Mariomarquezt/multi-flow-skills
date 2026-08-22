<!-- TEMPLATE. Replace every <blank>. Delete this comment. -->

# <MODEL> sliced review — run order

RULE: one slice at a time. Never two at once.
<If there is a pre-flight guard, say its threshold. If there is NOT one, say so here in
 plain words — "there is no pre-flight quota check on this backend; a 429 is the only
 signal" — so the next reader does not assume protection that does not exist.>

    ./docs/<model>-review/run-slice.sh <first-slice-name>

Cost per slice is UNKNOWN until the first one runs. `ledger.tsv` records the cost of every
run, so after slice 1 the estimate below is replaced by a measurement.

## Tier 1 — <the worst-outcome class, named>
 1. <slice-name>        <lines>   <one line on what it covers>
 ...

## Tier 2 — credentials and anything that writes to someone else's system
 ...

## Tier 3 — concurrency, transactions, schema, silent wrong data
 ...

## Tier 4 — UI, performance, tests, documentation drift
 ...

## Why this order

<Two or three sentences. Name the worst outcome this project can produce and say that
 Tier 1 is where it lives. Then state explicitly what is still covered if the budget runs
 out after Tier 2 — that guarantee is the entire reason the order exists.>

## Estimate

<Slices remaining> slices at <estimate> each ≈ <total>. Budget remaining: <amount>.
[hypothesis] until slice 1 lands in `ledger.tsv`.
