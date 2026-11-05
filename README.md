# Project EFC — Event-Driven Feature Computation

An offline research prototype comparing a conventional rolling-average recalculation engine with an incremental event-driven engine.

## Research question
Can an event-driven feature engine produce exactly the same rolling-average values as a conventional recalculation engine while reducing repeated rolling-sum arithmetic?

## Requirements
- Python 3.10+
- Runtime and tests use the Python standard library. pytest is optional.

## Quick start
```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m efc
python benchmarks/benchmark.py --events 200000 --repeats 5 --windows 10 50 100
```
On Windows, use `py -3` in place of `python` if necessary. The benchmark writes `results/latest_benchmark.csv`.

## Architecture
- ReferenceEngine recalculates the current sum from the entire bounded window after each event.
- EventDrivenEngine uses a preallocated circular buffer and running sum. Once full, it subtracts the expired value and adds the incoming value.
- Both return exact rational averages using Python Fraction.

Once the window is full, rolling-sum arithmetic per event is O(1) rather than O(N).

## Project layout
- src/efc/: event, result, engine, synthetic data and demo modules.
- tests/: exact-equivalence and validation tests.
- benchmarks/: repeated host-side benchmark.
- research/: scope, hypothesis and methodology.
- .github/workflows/: automated Python 3.10–3.13 test matrix.

## Interpretation limits
Operation counters include only rolling-sum additions/subtractions; they are not CPU instruction counts. Python timings are not FPGA, network, exchange or end-to-end trading latency measurements. Synthetic data does not show price predictability or profitability. This is not a live trading system.
