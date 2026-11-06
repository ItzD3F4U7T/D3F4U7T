"""Stage 3 synthetic reference-vs-incremental benchmark."""
from __future__ import annotations

import argparse
import platform
import random
import statistics
import sys
import time

from efc.stage3 import (BookEvent, EventDrivenBookEngine,
                        ReferenceBookEngine, replay)


def make_events(count: int, seed: int = 20261107) -> list[BookEvent]:
    rng = random.Random(seed)
    events: list[BookEvent] = []
    live: dict[str, int] = {}
    next_id = 0
    for seq in range(count):
        # Seed both sides first; then use a deterministic add/reduce mixture.
        add = seq < 2 or not live or rng.random() < 0.62
        if add:
            side = "B" if seq % 2 == 0 else "S"
            price = rng.randint(95, 99) if side == "B" else rng.randint(101, 105)
            qty = rng.randint(1, 100)
            oid = f"o{next_id}"
            next_id += 1
            events.append(BookEvent(seq, seq * 1_000, "ADD", oid, side, price, qty))
            live[oid] = qty
        else:
            oid = rng.choice(tuple(live))
            remaining = live[oid]
            qty = rng.randint(1, remaining)
            action = "EXECUTE" if rng.random() < 0.5 else "CANCEL"
            events.append(BookEvent(seq, seq * 1_000, action, oid, quantity=qty))
            if qty == remaining:
                del live[oid]
            else:
                live[oid] -= qty
    return events


def timed(factory, events, repeats: int) -> list[int]:
    results = []
    for _ in range(repeats):
        engine = factory()
        start = time.perf_counter_ns()
        replay(engine, events)
        results.append(time.perf_counter_ns() - start)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=50_000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--depth", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261107)
    args = parser.parse_args()
    if args.events < 2 or args.repeats < 1 or args.depth < 1:
        parser.error("events must be >=2; repeats and depth must be >=1")

    events = make_events(args.events, args.seed)
    ref_factory = lambda: ReferenceBookEngine(args.depth)
    inc_factory = lambda: EventDrivenBookEngine(args.depth)

    # Correctness gate before timing.
    ref_out = replay(ref_factory(), events)
    inc_out = replay(inc_factory(), events)
    if ref_out != inc_out:
        raise SystemExit("FAIL: reference and incremental snapshots differ")

    # Warm both engines on the same prefix, then alternate measured order.
    warm = events[:min(2_000, len(events))]
    replay(ref_factory(), warm)
    replay(inc_factory(), warm)
    ref_times, inc_times = [], []
    for repeat in range(args.repeats):
        first, second = ((ref_factory, inc_factory) if repeat % 2 == 0
                         else (inc_factory, ref_factory))
        first_time = timed(first, events, 1)[0]
        second_time = timed(second, events, 1)[0]
        if repeat % 2 == 0:
            ref_times.append(first_time)
            inc_times.append(second_time)
        else:
            inc_times.append(first_time)
            ref_times.append(second_time)

    ref_median = statistics.median(ref_times)
    inc_median = statistics.median(inc_times)
    ref_metrics = ReferenceBookEngine(args.depth)
    inc_metrics = EventDrivenBookEngine(args.depth)
    replay(ref_metrics, events)
    replay(inc_metrics, events)

    print(f"python={sys.version.split()[0]}, platform={platform.platform()}")
    print(f"events={args.events}, depth={args.depth}, repeats={args.repeats}, seed={args.seed}")
    print(f"reference median: {ref_median:.0f} ns ({ref_median/args.events:.1f} ns/event)")
    print(f"incremental median: {inc_median:.0f} ns ({inc_median/args.events:.1f} ns/event)")
    print(f"runtime ratio (reference/incremental): {ref_median/inc_median:.3f}x")
    print(f"reference full-book rebuilds: {ref_metrics.metrics.full_book_rebuilds}")
    print(f"incremental full-book rebuilds: {inc_metrics.metrics.full_book_rebuilds}")
    print(f"incremental price-level updates: {inc_metrics.metrics.level_updates}")
    print(f"adds={inc_metrics.metrics.adds}, cancels={inc_metrics.metrics.cancels}, "
          f"executions={inc_metrics.metrics.executions}")
    print("snapshot equality: PASS")


if __name__ == "__main__":
    main()
