"""Run a small equivalence demonstration with python -m efc."""
from .engine import EventDrivenEngine, ReferenceEngine, run_engine
from .synthetic import generate_events


def main() -> None:
    events = list(generate_events(25))
    reference = ReferenceEngine(10)
    incremental = EventDrivenEngine(10)
    ref_results = run_engine(reference, events)
    inc_results = run_engine(incremental, events)
    identical = ref_results == inc_results
    print(f"Events processed: {len(events)}")
    print(f"Feature outputs identical: {identical}")
    print(f"Reference sum operations: {reference.metrics.sum_arithmetic_operations}")
    print(f"Event-driven sum operations: {incremental.metrics.sum_arithmetic_operations}")
    if not identical:
        raise SystemExit("Equivalence check failed")


if __name__ == "__main__":
    main()
