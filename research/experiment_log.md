# Experiment Log

| Date | Python | Events | Window sizes | Repeats | Correctness | Notes |
|---|---|---:|---|---:|---|---|
| 2026-11-05 | 3.13.5 | 200,000 | 10, 50, 100 | 5 | 18 unit tests passed | Host-side benchmark; see benchmark_2026-11-05.csv. |

## Interpretation checklist
- Tests pass before interpreting timing.
- Inputs and event order are identical.
- Operation-count reduction is reported separately from runtime speedup.
- Machine and Python version are recorded.
- No profitability or exchange-latency claim is inferred from this microbenchmark.
