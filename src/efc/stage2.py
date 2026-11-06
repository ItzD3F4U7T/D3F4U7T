"""Stage 2: exact reference and incremental multi-feature engines.

Offline event replay only. All prices/quantities are integer ticks/lots.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from fractions import Fraction
from typing import Protocol


@dataclass(frozen=True, slots=True)
class MarketEvent:
    sequence: int
    price_ticks: int | None = None
    trade_size: int | None = None
    bid_price_ticks: int | None = None
    ask_price_ticks: int | None = None
    bid_size: int | None = None
    ask_size: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise TypeError("sequence must be an integer")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        trade_fields = (self.price_ticks, self.trade_size)
        if (trade_fields[0] is None) != (trade_fields[1] is None):
            raise ValueError("price_ticks and trade_size must be supplied together")
        if self.price_ticks is not None:
            _positive_int(self.price_ticks, "price_ticks")
            _positive_int(self.trade_size, "trade_size")  # type: ignore[arg-type]
        book_fields = (self.bid_price_ticks, self.ask_price_ticks,
                       self.bid_size, self.ask_size)
        if any(x is not None for x in book_fields):
            if any(x is None for x in book_fields):
                raise ValueError("all four book fields must be supplied together")
            _positive_int(self.bid_price_ticks, "bid_price_ticks")  # type: ignore[arg-type]
            _positive_int(self.ask_price_ticks, "ask_price_ticks")  # type: ignore[arg-type]
            _positive_int(self.bid_size, "bid_size")  # type: ignore[arg-type]
            _positive_int(self.ask_size, "ask_size")  # type: ignore[arg-type]
            if self.ask_price_ticks < self.bid_price_ticks:  # type: ignore[operator]
                raise ValueError("crossed book is not accepted by this prototype")
        if self.price_ticks is None and not any(x is not None for x in book_fields):
            raise ValueError("event must contain a trade or book update")


def _positive_int(value: int | None, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class FeatureSnapshot:
    sequence: int
    trade_samples: int
    rolling_mean_ticks: Fraction | None
    rolling_variance_ticks_squared: Fraction | None
    rolling_volume: int
    price_change_ticks: int | None
    book_imbalance: Fraction | None
    spread_ticks: int | None


@dataclass(frozen=True, slots=True)
class EngineMetrics:
    events_processed: int
    trade_payload_events: int
    book_payload_events: int
    trade_feature_recalculations: int
    book_feature_recalculations: int
    rolling_sum_additions: int
    rolling_sum_subtractions: int
    rolling_sumsq_additions: int
    rolling_sumsq_subtractions: int

    @property
    def counted_arithmetic_operations(self) -> int:
        return (self.rolling_sum_additions + self.rolling_sum_subtractions
                + self.rolling_sumsq_additions + self.rolling_sumsq_subtractions)


class FeatureEngine(Protocol):
    def on_event(self, event: MarketEvent) -> FeatureSnapshot: ...
    @property
    def metrics(self) -> EngineMetrics: ...


class _Base:
    def __init__(self, window_size: int) -> None:
        if isinstance(window_size, bool) or not isinstance(window_size, int):
            raise TypeError("window_size must be an integer")
        if window_size < 1:
            raise ValueError("window_size must be positive")
        self.window_size = window_size
        self._last_sequence: int | None = None
        self._events = 0
        self._trade_payloads = self._book_payloads = 0
        self._trade_recalculations = self._book_recalculations = 0
        self._sum_add = self._sum_sub = self._sq_add = self._sq_sub = 0
        self._last_price: int | None = None
        self._price_change: int | None = None
        self._book: tuple[int, int, int, int] | None = None
        self._book_imbalance: Fraction | None = None
        self._spread: int | None = None

    def _accept(self, event: MarketEvent) -> None:
        if not isinstance(event, MarketEvent):
            raise TypeError("event must be a MarketEvent")
        if self._last_sequence is not None and event.sequence <= self._last_sequence:
            raise ValueError("event sequence must be strictly increasing")
        self._last_sequence = event.sequence
        self._events += 1

    def _update_nonwindow_state(self, event: MarketEvent) -> None:
        if event.price_ticks is not None:
            self._price_change = (None if self._last_price is None
                                  else event.price_ticks - self._last_price)
            self._last_price = event.price_ticks
            self._trade_payloads += 1
        if event.bid_price_ticks is not None:
            self._book = (event.bid_price_ticks, event.ask_price_ticks,
                          event.bid_size, event.ask_size)  # type: ignore[arg-type]
            self._book_payloads += 1

    def _snapshot(self, sequence: int, samples: int, total: int,
                  sumsq: int, volume: int) -> FeatureSnapshot:
        imbalance, spread = self._book_imbalance, self._spread
        if samples:
            mean = Fraction(total, samples)
            variance = Fraction(sumsq, samples) - mean * mean
        else:
            mean = variance = None
        return FeatureSnapshot(sequence, samples, mean, variance, volume,
                               self._price_change, imbalance, spread)

    @property
    def metrics(self) -> EngineMetrics:
        return EngineMetrics(self._events, self._trade_payloads, self._book_payloads,
                             self._trade_recalculations, self._book_recalculations,
                             self._sum_add, self._sum_sub, self._sq_add, self._sq_sub)


class ReferenceFeatureEngine(_Base):
    """Straightforward oracle that recalculates trade-window aggregates."""
    def __init__(self, window_size: int) -> None:
        super().__init__(window_size)
        self._prices: deque[int] = deque(maxlen=window_size)
        self._sizes: deque[int] = deque(maxlen=window_size)

    def on_event(self, event: MarketEvent) -> FeatureSnapshot:
        self._accept(event)
        if event.price_ticks is not None:
            self._prices.append(event.price_ticks)
            self._sizes.append(event.trade_size)  # type: ignore[arg-type]
        self._update_nonwindow_state(event)
        # Conventional baseline: recalculate trade and quote-derived features
        # on every incoming event, even when their source payload did not change.
        self._trade_recalculations += 1
        self._book_recalculations += 1
        self._sum_add += max(0, len(self._prices) - 1)
        self._sq_add += max(0, len(self._prices) - 1)
        if self._book is None:
            self._book_imbalance = self._spread = None
        else:
            bid, ask, bid_size, ask_size = self._book
            self._book_imbalance = Fraction(bid_size - ask_size, bid_size + ask_size)
            self._spread = ask - bid
        total = sum(self._prices)
        sumsq = sum(x * x for x in self._prices)
        volume = sum(self._sizes)
        return self._snapshot(event.sequence, len(self._prices), total, sumsq, volume)


class EventDrivenFeatureEngine(_Base):
    """Incremental engine; only event-dependent feature groups are updated."""
    def __init__(self, window_size: int) -> None:
        super().__init__(window_size)
        self._prices = [0] * window_size
        self._sizes = [0] * window_size
        self._next = self._samples = 0
        self._sum = self._sumsq = self._volume = 0

    def on_event(self, event: MarketEvent) -> FeatureSnapshot:
        self._accept(event)
        if event.price_ticks is not None:
            price, size = event.price_ticks, event.trade_size
            if self._samples == self.window_size:
                old_price, old_size = self._prices[self._next], self._sizes[self._next]
                self._sum -= old_price
                self._sumsq -= old_price * old_price
                self._volume -= old_size
                self._sum_sub += 1
                self._sq_sub += 1
            else:
                self._samples += 1
            self._sum += price  # type: ignore[arg-type]
            self._sumsq += price * price  # type: ignore[operator]
            self._volume += size  # type: ignore[operator]
            self._sum_add += 1
            self._sq_add += 1
            self._prices[self._next] = price  # type: ignore[assignment]
            self._sizes[self._next] = size  # type: ignore[assignment]
            self._next = (self._next + 1) % self.window_size
        self._update_nonwindow_state(event)
        if event.price_ticks is not None:
            self._trade_recalculations += 1
        if event.bid_price_ticks is not None:
            bid, ask, bid_size, ask_size = self._book  # type: ignore[misc]
            self._book_imbalance = Fraction(bid_size - ask_size, bid_size + ask_size)
            self._spread = ask - bid
            self._book_recalculations += 1
        return self._snapshot(event.sequence, self._samples, self._sum,
                              self._sumsq, self._volume)


def replay(engine: FeatureEngine, events: list[MarketEvent]) -> list[FeatureSnapshot]:
    return [engine.on_event(event) for event in events]
