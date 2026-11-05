# Experimental Methodology

## Algorithms
The reference engine appends each price to a bounded deque and recalculates the sum by traversing the retained window. A sum of k values uses k-1 additions.

The event-driven engine allocates a fixed-size circular buffer at construction. During warm-up it builds the running sum. When full, it subtracts the expired value and adds the incoming value. Both engines return Fraction(sum, available_sample_count), so comparison is exact.

## Correctness protocol
- Use integer price ticks.
- Compare complete immutable snapshots, not rounded display values.
- Test hand-calculated examples, random streams, multiple window sizes, warm-up, rollover, reset and invalid event ordering.
- Keep the reference implementation simple so it can act as an oracle.

## Operation-count protocol
Counters include only additions/subtractions used to recalculate or maintain the rolling sum. They omit index arithmetic, comparisons, container operations, object creation, Fraction normalization and interpreter instructions. They are an algorithmic proxy, not hardware counters.

## Timing protocol
- Generate events before timing.
- Feed identical pre-generated events to both engines.
- Warm up both implementations.
- Alternate benchmark order across repetitions.
- Consume outputs without retaining an output list during timed runs.
- Report median total runtime, derived ns/event and events/second for multiple window sizes.

Python timing is host/runtime dependent. A compiled implementation and FPGA design need separate, hardware-specific measurement procedures.
