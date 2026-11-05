# Project EFC — Research Specification

## Objective
Develop an event-driven feature-computation engine that produces exactly the same feature values as a conventional recalculation engine while reducing repeated arithmetic work.

## Hypothesis
For a rolling average over N trade prices, maintaining a running sum can produce the exact same result as recalculating the sum from the stored window on every event. Once the window is full, the incremental method needs two sum updates (subtract the expired value; add the incoming value) instead of summing all N values again.

## Scope
- Offline event replay only.
- Synthetic integer price ticks for reproducible tests.
- One rolling-average feature in this first experiment.
- Exact Fraction outputs.
- Algorithmic operation counters and host-side timing benchmarks.

This is not a live trading system, exchange connector, production order book or proof of profitability.

## Input and output
Each event has a strictly increasing sequence number and a positive integer price_ticks value. After every event, both engines return the event sequence, window size, sample count, rolling sum and exact average.

## Variables
Independent: window size, event count, seed/input sequence and implementation.
Dependent: snapshot equality, counted additions/subtractions, processing time and throughput.

## Success criteria
1. All snapshots are exactly equal for every valid event.
2. Warm-up and full-window rollover are correct.
3. Duplicate and out-of-order events are rejected.
4. The event-driven engine performs fewer counted rolling-sum arithmetic operations after warm-up.
5. Timings use the same pre-generated events, identical window sizes and repeated trials.

## Limitations
Operation counters are not CPU instruction counts. Python timings are not FPGA or exchange latency. Synthetic data does not establish predictive power or trading profit.
