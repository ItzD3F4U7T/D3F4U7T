# Stage 2 Experimental Methodology

1. Generate a deterministic mixed stream of trade-only, quote-only and combined events before timing.
2. Replay the identical sequence through the reference and incremental engines.
3. Compare the complete output snapshot after every event using exact \`Fraction\` values.
4. Run multiple window sizes and randomized event streams in the correctness suite.
5. Warm up both implementations and alternate benchmark order across repetitions.
6. Report median runtime and per-event time separately from selected arithmetic counters and feature-group update counts.

The reference engine intentionally recomputes rolling aggregates and quote-derived values for every incoming event. The incremental engine only updates the feature group whose source payload changed. The benchmark is a Python host microbenchmark, not a hardware latency test. Re-run on the target machine before drawing performance conclusions.
