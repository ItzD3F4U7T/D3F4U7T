# Project EFC — Event-Driven Feature Computation

EFC is an offline research prototype for comparing conventional recalculation with incremental event-driven feature computation.

## Stage 1
Stage 1 compares a rolling-average reference engine with an incremental circular-buffer engine. It checks exact equality and counts selected rolling-sum arithmetic operations.

## Stage 2
Stage 2 adds a multi-feature dependency engine with rolling mean, rolling population variance, rolling volume, last-trade price change, best-quote size imbalance and spread. The reference engine recalculates feature groups on every event; the incremental engine updates only the group whose source payload changed.

## Requirements and quick start
- Python 3.10+
- Runtime and tests use the standard library.

\`\`\`bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m efc
python benchmarks/benchmark.py --events 200000 --repeats 5 --windows 10 50 100
python benchmarks/benchmark_stage2.py --events 100000 --window 100 --repeats 5
\`\`\`

On Windows, use \`py -3\` in place of \`python\` if necessary.

## Project layout
- \`src/efc/\`: Stage 1 and Stage 2 engines, events, models and demo.
- \`tests/\`: exact-equivalence, validation and dependency tests.
- \`benchmarks/\`: host-side performance experiments.
- \`research/\`: specifications, methodology, experiment logs and reading list.
- \`.github/workflows/\`: automated tests for Python 3.10–3.13.

## Interpretation limits
Operation counters cover selected arithmetic only; they are not CPU instruction counts. Python timings are host-dependent and are not FPGA, network, exchange or end-to-end latency measurements. Synthetic events do not establish price predictability or profitability. This repository is not a live trading or order-execution system.
