"""Reference and event-driven rolling-average engines."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Protocol

from .events import TradeEvent
from .models import EngineMetrics, FeatureSnapshot


class RollingAverageEngine(Protocol):
    window_size: int
    def on_event(self, event: TradeEvent) -> FeatureSnapshot: ...
    def reset(self) -> None: ...
    @property
    def metrics(self) -> EngineMetrics: ...


def _validate_window_size(window_size: int) -> None:
    if isinstance(window_size, bool) or not isinstance(window_size, int):
        raise TypeError("window_size must be an integer")
    if window_size < 1:
        raise ValueError("window_size must be at least 1")


@dataclass(slots=True)
class _Counters:
    events_processed: int = 0
    sum_additions: int = 0
    sum_subtractions: int = 0
    average_evaluations: int = 0

    def snapshot(self) -> EngineMetrics:
        return EngineMetrics(self.events_processed, self.sum_additions,
                             self.sum_subtractions, self.average_evaluations)


class _BaseEngine:
    def __init__(self, window_size: int) -> None:
        _validate_window_size(window_size)
        self.window_size = window_size
        self._last_sequence: int | None = None
        self._counters = _Counters()

    def _validate_sequence(self, event: TradeEvent) -> None:
        if not isinstance(event, TradeEvent):
            raise TypeError("event must be a TradeEvent")
        if self._last_sequence is not None and event.sequence <= self._last_sequence:
            raise ValueError("events must have strictly increasing sequence numbers")
        self._last_sequence = event.sequence
        self._counters.events_processed += 1

    def _make_snapshot(self, event: TradeEvent, samples: int, total: int) -> FeatureSnapshot:
        self._counters.average_evaluations += 1
        return FeatureSnapshot(event.sequence, self.window_size, samples, total,
                               Fraction(total, samples))

    @property
    def metrics(self) -> EngineMetrics:
        return self._counters.snapshot()


class ReferenceEngine(_BaseEngine):
    """Simple oracle: recalculate the current window sum on each event."""
    def __init__(self, window_size: int) -> None:
        super().__init__(window_size)
        self._prices: deque[int] = deque(maxlen=window_size)

    def on_event(self, event: TradeEvent) -> FeatureSnapshot:
        self._validate_sequence(event)
        self._prices.append(event.price_ticks)
        self._counters.sum_additions += max(0, len(self._prices) - 1)
        return self._make_snapshot(event, len(self._prices), sum(self._prices))

    def reset(self) -> None:
        self._prices.clear()
        self._last_sequence = None
        self._counters = _Counters()


class EventDrivenEngine(_BaseEngine):
    """Maintain the rolling sum with a fixed-size circular buffer."""
    def __init__(self, window_size: int) -> None:
        super().__init__(window_size)
        self._buffer = [0] * window_size
        self._next_index = 0
        self._samples = 0
        self._rolling_sum = 0

    def on_event(self, event: TradeEvent) -> FeatureSnapshot:
        self._validate_sequence(event)
        if self._samples < self.window_size:
            if self._samples:
                self._rolling_sum += event.price_ticks
                self._counters.sum_additions += 1
            else:
                self._rolling_sum = event.price_ticks
            self._buffer[self._next_index] = event.price_ticks
            self._samples += 1
        else:
            expired = self._buffer[self._next_index]
            self._rolling_sum -= expired
            self._counters.sum_subtractions += 1
            self._rolling_sum += event.price_ticks
            self._counters.sum_additions += 1
            self._buffer[self._next_index] = event.price_ticks
        self._next_index = (self._next_index + 1) % self.window_size
        return self._make_snapshot(event, self._samples, self._rolling_sum)

    def reset(self) -> None:
        self._buffer = [0] * self.window_size
        self._next_index = 0
        self._samples = 0
        self._rolling_sum = 0
        self._last_sequence = None
        self._counters = _Counters()


def run_engine(engine: RollingAverageEngine, events: Iterable[TradeEvent]) -> list[FeatureSnapshot]:
    return [engine.on_event(event) for event in events]
