"""Offline Stage 2 engine comparison. No live market connectivity."""
from __future__ import annotations
import argparse
import statistics
import time
from efc.stage2 import EventDrivenFeatureEngine, MarketEvent, ReferenceFeatureEngine


def make_events(n: int) -> list[MarketEvent]:
    events = []
    price = 100_000
    for i in range(n):
        price += (i % 5) - 2
        if i % 4 == 0:
            events.append(MarketEvent(i, price, (i % 11) + 1,
                                      price - 1, price + 1,
                                      (i % 17) + 1, (i % 13) + 1))
        elif i % 4 == 1:
            events.append(MarketEvent(i, bid_price_ticks=price - 1,
                                      ask_price_ticks=price + 1,
                                      bid_size=(i % 17) + 1, ask_size=(i % 13) + 1))
        else:
            events.append(MarketEvent(i, price, (i % 11) + 1))
    return events


def run(cls, events, window):
    engine = cls(window)
    start = time.perf_counter_ns()
    for event in events:
        engine.on_event(event)
    return time.perf_counter_ns() - start, engine.metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=100_000)
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if min(args.events, args.window, args.repeats) < 1:
        parser.error("all arguments must be positive")
    events = make_events(args.events)
    # Warm both implementations on the same prefix before collecting timings.
    warmup_events = events[:min(10_000, len(events))]
    run(ReferenceFeatureEngine, warmup_events, args.window)
    run(EventDrivenFeatureEngine, warmup_events, args.window)
    timings = {"reference": [], "incremental": []}
    metrics = {}
    for i in range(args.repeats):
        order = ((ReferenceFeatureEngine, EventDrivenFeatureEngine) if i % 2 == 0
                 else (EventDrivenFeatureEngine, ReferenceFeatureEngine))
        for cls in order:
            elapsed, m = run(cls, events, args.window)
            key = "reference" if cls is ReferenceFeatureEngine else "incremental"
            timings[key].append(elapsed)
            metrics[key] = m
    ref = statistics.median(timings["reference"])
    inc = statistics.median(timings["incremental"])
    print(f"events={args.events}, window={args.window}, repeats={args.repeats}")
    print(f"reference median: {ref:.0f} ns ({ref/args.events:.1f} ns/event)")
    print(f"incremental median: {inc:.0f} ns ({inc/args.events:.1f} ns/event)")
    print(f"runtime ratio: {ref/inc:.3f}x")
    print(f"reference counted arithmetic: {metrics['reference'].counted_arithmetic_operations}")
    print(f"incremental counted arithmetic: {metrics['incremental'].counted_arithmetic_operations}")
    print(f"trade payloads: {metrics['incremental'].trade_payload_events}; book payloads: {metrics['incremental'].book_payload_events}")
    print(f"reference feature recalculations: trade={metrics['reference'].trade_feature_recalculations}, book={metrics['reference'].book_feature_recalculations}")
    print(f"incremental feature updates: trade={metrics['incremental'].trade_feature_recalculations}, book={metrics['incremental'].book_feature_recalculations}")


if __name__ == "__main__":
    main()
