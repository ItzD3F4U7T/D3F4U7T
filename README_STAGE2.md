# EFC Stage 2 — Multi-Feature Dependency Engine

Stage 2 adds an offline multi-feature engine alongside Stage 1. It computes six outputs:

1. Rolling mean price over the last N trades.
2. Rolling population variance over the last N trades.
3. Rolling total trade volume over the last N trades.
4. Last trade-price change.
5. Best-quote size imbalance.
6. Best-quote spread.

A conventional reference engine recalculates the feature groups on every event. The event-driven engine only updates the trade feature group on trade-bearing events and the quote feature group on quote-bearing events. It maintains rolling sum, sum of squares and volume in a fixed-size ring buffer. Exact \`Fraction\` arithmetic is used for mean, variance and imbalance.

## Run

\`\`\`bash
python -m pip install -e .
python -m unittest discover -s tests -v
python benchmarks/benchmark_stage2.py --events 100000 --window 100 --repeats 5
\`\`\`

All prices and sizes are integer ticks/lots. Events must have strictly increasing sequence numbers. A trade payload includes price and size; a quote payload includes bid/ask prices and sizes. Crossed quotes are rejected in this research prototype.

## Important limitations

This is an offline computational-equivalence experiment. It does not connect to an exchange, generate orders, estimate real trading returns, or prove profitability. Operation counters cover selected rolling-sum and sum-of-squares arithmetic, not all CPU instructions. Python timing is host-dependent and is not FPGA or exchange latency.

See \`research/stage2_specification.md\`, \`research/stage2_references.md\` and \`research/stage2_benchmark_2026-11-06.csv\`.
