# Stage 3 Specification — Multi-Level Order-Book Replay

## Research question
Can incremental price-level maintenance exactly match an independent order-level reference book while avoiding full-book aggregate reconstruction on each event?

## Scope
One instrument, one continuous book, integer price ticks and quantities, offline deterministic replay.

## State
The canonical order state is keyed by order ID. Each order has side, price and remaining quantity. Price-level state aggregates total quantity and number of live orders.

## Events
- ADD: introduce a unique live order.
- CANCEL: reduce resting quantity.
- EXECUTE: reduce resting quantity as an execution.
Partial reductions preserve the order ID; full reductions remove it.

## Invariants
1. Live order IDs are unique.
2. Every live order has positive remaining quantity.
3. Level quantity equals the sum of remaining order quantities at that price.
4. Level order count equals the number of live orders at that price.
5. Best bid is strictly below best ask whenever both sides exist.
6. Sequence strictly increases; timestamps do not decrease.
7. Invalid events leave state and stream cursors unchanged.
8. Reference and incremental snapshots are exactly equal after every accepted event.

## Features
Top-N levels per side, best quotes, spread, midpoint, order counts, resting quantities, executed quantity, event OFI and cumulative OFI.

## Validation
Hand-calculated examples; partial/full reductions; malformed and out-of-order events; deterministic randomized streams; per-event reference/incremental snapshot equality; metrics proving reference rebuilds and incremental level updates.

## Explicit non-goals
No live exchange connectivity, order routing, trading strategy, profit claim, latency guarantee, or exchange certification.
