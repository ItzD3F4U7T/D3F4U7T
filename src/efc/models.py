"""Immutable result and instrumentation models."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class FeatureSnapshot:
    event_sequence: int
    window_size: int
    samples: int
    rolling_sum_ticks: int
    average_ticks: Fraction


@dataclass(frozen=True, slots=True)
class EngineMetrics:
    """Selected algorithmic counters, not hardware instruction counts."""
    events_processed: int
    sum_additions: int
    sum_subtractions: int
    average_evaluations: int

    @property
    def sum_arithmetic_operations(self) -> int:
        return self.sum_additions + self.sum_subtractions
