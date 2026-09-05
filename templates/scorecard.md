# Model scorecard — <project> — <YYYY-MM-DD>

Mode: `<invocation>` · slices: <N> · reviewers: <N> · triage done by: <who>

Scores use findings that SURVIVED triage (Step 10), never raw claims.
Weights: critical 8 · high 4 · medium 2 · low 1 · info 0.
Score = Σ weights of verified findings. Precision = verified ÷ reported.
Unique = verified findings no other model reported. Missed = verified critical/high found by others, not by this model.

| rank | model | route · effort | reported | verified | refuted | precision | crit | high | med | low | unique | missed crit/high | score | total time | avg / slice | slowest slice | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | <model> | <route> · <effort> | 0 | 0 | 0 | 0% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0h 00m | 0m 00s | 0m 00s (<slice id>) | <ledger> |
| 2 | <model> | <route> · <effort> | 0 | 0 | 0 | 0% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0h 00m | 0m 00s | 0m 00s (<slice id>) | <ledger> |

Severity columns count VERIFIED findings only. Refuted = disproved in Step 10 or 11b.
Time columns come from `ledger.tsv`: total = sum of that model's slice wall clocks; avg = total ÷ slices it ran; slowest = its longest single slice. Time is queue time per model, not the run's overall wall clock — lanes run in parallel.

## Why the ranking

- **#1 <model>** — one sentence: what it found that mattered, and what it missed.
- **#2 <model>** — same.

## Every model missed

- <the verified critical/high that NO reviewer reported, found by the human or the database in triage — or "none">

## Caveats

- Ties on score break by unique finds, then precision.
- <N> findings were refuted after being reported by more than one model — agreement was not evidence.
- <anything that makes this run not comparable to another: partial tiers, a lane that died, buffered output kill, different slice set>
