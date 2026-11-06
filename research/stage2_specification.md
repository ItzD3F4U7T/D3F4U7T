# EFC Stage 2 — Research Specification

## Objective
Demonstrate that an event-driven multi-feature engine can produce exactly the same outputs as a conventional recalculation oracle while reducing repeated computation.

## Features
- Rolling mean: \`sum(price_ticks) / sample_count\`.
- Rolling population variance: \`sum(price_ticks^2) / sample_count - mean^2\`.
- Rolling volume: sum of trade sizes in the same trade window.
- Last trade-price change: current trade price minus previous trade price.
- Best-quote size imbalance: \`(bid_size - ask_size) / (bid_size + ask_size)\`.
- Best-quote spread: \`ask_price_ticks - bid_price_ticks\`.

Mean, variance and imbalance use exact rational arithmetic (\`Fraction\`). Prices and sizes are integers to avoid binary floating-point ambiguity in the feature values.

## Event contract
\`MarketEvent\` is immutable and sequence-numbered. A trade payload contains both integer \`price_ticks\` and positive integer \`trade_size\`. A quote payload contains bid/ask prices and bid/ask sizes together. An event may contain a trade, quote, or both. Crossed books are rejected. Sequence numbers must strictly increase.

## Dependency rules
A conventional reference engine recalculates both feature groups on every event. The incremental engine updates rolling trade aggregates and price change only when a trade payload arrives. It updates book imbalance and spread only when a quote payload arrives. The most recent quote state persists across trade-only events.

## Correctness criteria
The complete immutable output snapshots from both engines must be equal after every event. Tests cover hand calculations, randomized mixed streams, multiple window lengths, malformed payloads, sequence ordering, quote-state persistence and selective feature updates.

## Measurement limits
Arithmetic counters count selected rolling-sum and sum-of-squares additions/subtractions. They omit comparisons, indexing, divisions, volume arithmetic, Python object overhead, memory traffic and CPU instructions. They are an algorithmic proxy, not hardware counters. Python timings are host-specific. No profitability, predictive-power, production-suitability, FPGA-latency or exchange-latency claim follows from this offline prototype.
