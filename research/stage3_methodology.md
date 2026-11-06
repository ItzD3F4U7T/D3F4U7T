# Stage 3 Methodology

## Experimental design
Feed the same immutable event stream to two independently maintained engines:
- Reference: update the order map and rebuild every price-level aggregate after every event.
- Incremental: update only the price level touched by the event.

Compare every immutable snapshot, not just the final book. A mismatch at any event is a correctness failure.

## Workload design
Use deterministic synthetic streams with a fixed random seed. Mix adds, cancels and executions; vary price levels, order sizes, book depth and event count. Preserve valid event semantics and non-crossed books.

## Measurements
Record event count, operation mix, full-book rebuild count, incremental price-level update count, and median wall-clock time across repeated runs. Warm both engines with the same prefix and alternate timing order to reduce simple order bias.

## Interpretation
A rebuild count versus a level-update count demonstrates architectural work avoided, not total CPU instructions. Timing includes Python runtime, dictionary operations, sorting for emitted depth snapshots and allocation. Report host, Python version, workload, depth, repeats and seed. Do not generalize one synthetic result to production or exchange latency.

## Correctness gates
All tests pass; snapshots are identical at each event; rejected events do not mutate stream cursors or state; event replay is deterministic.
