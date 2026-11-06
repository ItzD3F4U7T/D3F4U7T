# EFC Stage 3 — Multi-Level Order-Book Replay

Stage 3 extends EFC from top-of-book snapshots to a deterministic, offline multi-level limit-order-book state machine. It supports order additions, partial/full cancellations and partial/full executions, price-level aggregation, top-N depth snapshots, and event-level best-quote order-flow imbalance (OFI).

## Event contract

- Sequence numbers are strictly increasing.
- Event timestamps are non-decreasing integer nanoseconds.
- `ADD` carries a unique live order ID, side (`B` bid or `S` ask), positive integer price ticks and quantity.
- `CANCEL` and `EXECUTE` refer to a live order ID and a positive quantity no larger than its remaining quantity.
- Partial reductions preserve the order; a zero remainder removes it.
- A new order that would lock or cross the opposite best quote is rejected.
- A rejected event does not advance the engine's sequence or timestamp.

## Architecture

- `ReferenceBookEngine`: applies order-level state changes, then rebuilds every price-level aggregate from all live orders. This is the correctness oracle.
- `EventDrivenBookEngine`: updates only the affected price-level aggregate and maintains the order map. It does not rebuild the full book.
- Both emit immutable snapshots and compute the same OFI feature from consecutive best-quote states.

## Features

- Bid and ask depth, sorted by price priority.
- Aggregate quantity and order count at each price.
- Best bid/ask, spread and midpoint.
- Total resting quantity and live order count.
- Executed quantity and cumulative OFI.

For consecutive two-sided book states, the best-quote OFI contribution follows the event-based expression described by Cont, Kukanov and Stoikov (2014):

`e_n = 1(P^B_n >= P^B_{n-1})q^B_n - 1(P^B_n <= P^B_{n-1})q^B_{n-1} - 1(P^A_n <= P^A_{n-1})q^A_n + 1(P^A_n >= P^A_{n-1})q^A_{n-1}`

If either snapshot lacks one side, OFI is `None` and the comparison baseline resets. The first subsequent complete two-sided snapshot establishes a new baseline; OFI resumes on the following event.

## Run

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python benchmarks/benchmark_stage3.py --events 50000 --repeats 5
```

## Interpretation and limitations

This is a deterministic educational/research simulator, not a venue-grade matching engine. It assumes order IDs are globally unique while live, models one instrument, has no hidden/iceberg orders, market orders, auctions, implied liquidity, venue-specific priority rules, corrections, trade busts, feed gaps or recovery protocol. It does not connect to an exchange, route orders, produce live signals or establish profitability.

OFI is a descriptive microstructure feature, not a guaranteed predictor. A performance comparison is meaningful only for the exact synthetic workload and machine reported. The reference engine intentionally rebuilds the book on every event; the incremental engine updates one price level. Python wall-clock timings are not exchange latency or hardware-accelerator measurements.
