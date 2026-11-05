"""Host-side comparison, not FPGA or exchange latency measurement."""
from __future__ import annotations
import argparse
import csv
import gc
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from efc.engine import EventDrivenEngine, ReferenceEngine  # noqa: E402
from efc.synthetic import generate_events  # noqa: E402


def time_one(engine_type, window: int, events: list) -> tuple[int, object]:
    engine = engine_type(window)
    gc.collect()
    start = time.perf_counter_ns()
    for event in events:
        engine.on_event(event)
    return time.perf_counter_ns() - start, engine.metrics


def benchmark(event_count: int, repeats: int, windows: list[int]) -> list[dict]:
    events = list(generate_events(event_count))
    rows = []
    for window in windows:
        timings = {"reference": [], "event_driven": []}
        counters = {}
        for cls in (ReferenceEngine, EventDrivenEngine):
            time_one(cls, window, events[:min(10_000, event_count)])
        for i in range(repeats):
            order = ((ReferenceEngine, EventDrivenEngine) if i % 2 == 0
                     else (EventDrivenEngine, ReferenceEngine))
            for cls in order:
                elapsed, metrics = time_one(cls, window, events)
                key = "reference" if cls is ReferenceEngine else "event_driven"
                timings[key].append(elapsed)
                counters[key] = metrics
        ref_ns = int(statistics.median(timings["reference"]))
        inc_ns = int(statistics.median(timings["event_driven"]))
        ref_ops = counters["reference"].sum_arithmetic_operations
        inc_ops = counters["event_driven"].sum_arithmetic_operations
        reduction = 100 * (ref_ops - inc_ops) / ref_ops if ref_ops else 0.0
        rows.append({
            "events": event_count, "window_size": window, "repeats": repeats,
            "reference_median_ns_total": ref_ns,
            "event_driven_median_ns_total": inc_ns,
            "reference_ns_per_event": ref_ns / event_count,
            "event_driven_ns_per_event": inc_ns / event_count,
            "reference_events_per_second": event_count * 1e9 / ref_ns,
            "event_driven_events_per_second": event_count * 1e9 / inc_ns,
            "reference_sum_arithmetic_ops": ref_ops,
            "event_driven_sum_arithmetic_ops": inc_ops,
            "sum_arithmetic_op_reduction_pct": reduction,
            "timed_speedup_reference_over_event_driven": ref_ns / inc_ns,
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=200_000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--windows", type=int, nargs="+", default=[10, 50, 100])
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "latest_benchmark.csv")
    args = parser.parse_args()
    if args.events < 1 or args.repeats < 1 or any(w < 1 for w in args.windows):
        parser.error("events, repeats and all window sizes must be positive")
    rows = benchmark(args.events, args.repeats, args.windows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV written to {args.output}")
    for row in rows:
        print(f"window={row['window_size']} | ref={row['reference_ns_per_event']:.1f} ns/event | "
              f"event-driven={row['event_driven_ns_per_event']:.1f} ns/event | "
              f"sum-op reduction={row['sum_arithmetic_op_reduction_pct']:.1f}% | "
              f"speedup={row['timed_speedup_reference_over_event_driven']:.2f}x")


if __name__ == "__main__":
    main()
