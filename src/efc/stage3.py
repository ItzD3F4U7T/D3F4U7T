"""Stage 3: offline multi-level order-book replay and OFI features.

This module is a correctness-first research simulator. It does not connect to
venues, route orders, or make trading decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal, Protocol

Side = Literal["B", "S"]
Action = Literal["ADD", "CANCEL", "EXECUTE"]


@dataclass(frozen=True, slots=True)
class BookEvent:
    sequence: int
    timestamp_ns: int
    action: Action
    order_id: str
    side: Side | None = None
    price_ticks: int | None = None
    quantity: int | None = None

    def __post_init__(self) -> None:
        _integer(self.sequence, "sequence", minimum=0)
        _integer(self.timestamp_ns, "timestamp_ns", minimum=0)
        if self.action not in ("ADD", "CANCEL", "EXECUTE"):
            raise ValueError("action must be ADD, CANCEL, or EXECUTE")
        if not isinstance(self.order_id, str) or not self.order_id:
            raise ValueError("order_id must be a non-empty string")
        if self.action == "ADD":
            if self.side not in ("B", "S"):
                raise ValueError("ADD requires side 'B' or 'S'")
            _integer(self.price_ticks, "price_ticks", minimum=1)
            _integer(self.quantity, "quantity", minimum=1)
        else:
            if self.side is not None or self.price_ticks is not None:
                raise ValueError("CANCEL/EXECUTE identify an existing order by order_id only")
            _integer(self.quantity, "quantity", minimum=1)


def _integer(value: int | None, name: str, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    side: Side
    price_ticks: int
    remaining: int


@dataclass(frozen=True, slots=True)
class Level:
    price_ticks: int
    quantity: int
    order_count: int


@dataclass(frozen=True, slots=True)
class BookSnapshot:
    sequence: int
    timestamp_ns: int
    bids: tuple[Level, ...]
    asks: tuple[Level, ...]
    best_bid_ticks: int | None
    best_ask_ticks: int | None
    best_bid_size: int
    best_ask_size: int
    spread_ticks: int | None
    midpoint_ticks: Fraction | None
    order_count: int
    total_bid_quantity: int
    total_ask_quantity: int
    event_ofi: int | None
    cumulative_ofi: int
    executed_quantity: int


@dataclass(frozen=True, slots=True)
class BookMetrics:
    events_processed: int
    adds: int
    cancels: int
    executions: int
    rejected_events: int
    level_updates: int
    full_book_rebuilds: int


class BookEngine(Protocol):
    def on_event(self, event: BookEvent) -> BookSnapshot: ...
    @property
    def metrics(self) -> BookMetrics: ...


def _top(bids: dict[int, list[int]], asks: dict[int, list[int]]):
    bid = max(bids) if bids else None
    ask = min(asks) if asks else None
    bid_qty = bids[bid][0] if bid is not None else 0
    ask_qty = asks[ask][0] if ask is not None else 0
    return bid, ask, bid_qty, ask_qty


def _ofi(previous, current) -> int | None:
    # Cont-Kukanov-Stoikov best-quote OFI contribution. A missing side breaks
    # the comparison baseline; the next fully two-sided state re-establishes it.
    if previous is None or current is None:
        return None
    pb, pa, pbq, paq = previous
    cb, ca, cbq, caq = current
    if None in (pb, pa, cb, ca):
        return None
    return (
        (cbq if cb >= pb else 0) - (pbq if cb <= pb else 0)
        - (caq if ca <= pa else 0) + (paq if ca >= pa else 0)
    )


class _BaseBook:
    def __init__(self, depth: int = 5) -> None:
        _integer(depth, "depth", minimum=1)
        self.depth = depth
        self._orders: dict[str, Order] = {}
        self._last_sequence: int | None = None
        self._last_timestamp: int | None = None
        self._previous_top = None
        self._cumulative_ofi = 0
        self._executed_quantity = 0
        self._total_bid_quantity = 0
        self._total_ask_quantity = 0
        self._events = self._adds = self._cancels = self._executions = 0
        self._rejected = self._level_updates = self._rebuilds = 0

    def _validate_order_event(self, event: BookEvent) -> Order | None:
        if not isinstance(event, BookEvent):
            raise TypeError("event must be a BookEvent")
        if self._last_sequence is not None and event.sequence <= self._last_sequence:
            raise ValueError("sequence must be strictly increasing")
        if self._last_timestamp is not None and event.timestamp_ns < self._last_timestamp:
            raise ValueError("timestamps must be non-decreasing")
        existing = self._orders.get(event.order_id)
        if event.action == "ADD":
            if existing is not None:
                raise ValueError("duplicate live order_id")
            assert event.side is not None and event.price_ticks is not None
            bid, ask, _, _ = self._current_top()
            if event.side == "B" and ask is not None and event.price_ticks >= ask:
                raise ValueError("ADD would create a crossed or locked book")
            if event.side == "S" and bid is not None and event.price_ticks <= bid:
                raise ValueError("ADD would create a crossed or locked book")
        else:
            if existing is None:
                raise ValueError("unknown order_id")
            assert event.quantity is not None
            if event.quantity > existing.remaining:
                raise ValueError("quantity exceeds order's remaining quantity")
        return existing

    def _current_top(self):
        raise NotImplementedError

    def _apply_order_change(self, event: BookEvent, existing: Order | None) -> None:
        if event.action == "ADD":
            assert event.side is not None and event.price_ticks is not None and event.quantity is not None
            self._orders[event.order_id] = Order(event.order_id, event.side,
                                                  event.price_ticks, event.quantity)
            if event.side == "B":
                self._total_bid_quantity += event.quantity
            else:
                self._total_ask_quantity += event.quantity
            self._adds += 1
        else:
            assert existing is not None and event.quantity is not None
            remaining = existing.remaining - event.quantity
            if existing.side == "B":
                self._total_bid_quantity -= event.quantity
            else:
                self._total_ask_quantity -= event.quantity
            if remaining:
                self._orders[event.order_id] = Order(existing.order_id, existing.side,
                                                      existing.price_ticks, remaining)
            else:
                del self._orders[event.order_id]
            if event.action == "CANCEL":
                self._cancels += 1
            else:
                self._executions += 1
                self._executed_quantity += event.quantity

    def _make_snapshot(self, event: BookEvent, bids, asks, top, ofi):
        bid, ask, bid_qty, ask_qty = top
        bid_levels = tuple(Level(p, values[0], values[1]) for p, values in
                           sorted(bids.items(), reverse=True)[:self.depth])
        ask_levels = tuple(Level(p, values[0], values[1]) for p, values in
                           sorted(asks.items())[:self.depth])
        if ofi is not None:
            self._cumulative_ofi += ofi
        return BookSnapshot(
            event.sequence, event.timestamp_ns, bid_levels, ask_levels,
            bid, ask, bid_qty, ask_qty,
            ask - bid if bid is not None and ask is not None else None,
            Fraction(bid + ask, 2) if bid is not None and ask is not None else None,
            len(self._orders), self._total_bid_quantity, self._total_ask_quantity,
            ofi, self._cumulative_ofi, self._executed_quantity,
        )

    @property
    def metrics(self) -> BookMetrics:
        return BookMetrics(self._events, self._adds, self._cancels,
                           self._executions, self._rejected, self._level_updates,
                           self._rebuilds)


class ReferenceBookEngine(_BaseBook):
    """Oracle: rebuild all price-level aggregates from live orders per event."""
    def __init__(self, depth: int = 5) -> None:
        super().__init__(depth)
        self._bids: dict[int, list[int]] = {}
        self._asks: dict[int, list[int]] = {}

    def _current_top(self):
        return _top(self._bids, self._asks)

    def on_event(self, event: BookEvent) -> BookSnapshot:
        try:
            existing = self._validate_order_event(event)
        except (TypeError, ValueError):
            self._rejected += 1
            raise
        self._apply_order_change(event, existing)
        bids: dict[int, list[int]] = {}
        asks: dict[int, list[int]] = {}
        for order in self._orders.values():
            levels = bids if order.side == "B" else asks
            agg = levels.setdefault(order.price_ticks, [0, 0])
            agg[0] += order.remaining
            agg[1] += 1
        self._bids, self._asks = bids, asks
        self._rebuilds += 1
        top = self._current_top()
        ofi = _ofi(self._previous_top, top)
        self._previous_top = top if top[0] is not None and top[1] is not None else None
        self._last_sequence, self._last_timestamp = event.sequence, event.timestamp_ns
        self._events += 1
        return self._make_snapshot(event, bids, asks, top, ofi)


class EventDrivenBookEngine(_BaseBook):
    """Incremental price-level aggregates; only the touched level is updated."""
    def __init__(self, depth: int = 5) -> None:
        super().__init__(depth)
        self._bids: dict[int, list[int]] = {}
        self._asks: dict[int, list[int]] = {}

    def _current_top(self):
        return _top(self._bids, self._asks)

    def _change_level(self, side: Side, price: int, quantity_delta: int, order_delta: int) -> None:
        levels = self._bids if side == "B" else self._asks
        agg = levels.get(price)
        if agg is None:
            if quantity_delta <= 0 or order_delta <= 0:
                raise AssertionError("attempted to remove a missing price level")
            levels[price] = [quantity_delta, order_delta]
        else:
            agg[0] += quantity_delta
            agg[1] += order_delta
            if agg[0] == 0:
                del levels[price]
            elif agg[0] < 0 or agg[1] <= 0:
                raise AssertionError("negative aggregate book state")
        self._level_updates += 1

    def on_event(self, event: BookEvent) -> BookSnapshot:
        try:
            existing = self._validate_order_event(event)
        except (TypeError, ValueError):
            self._rejected += 1
            raise
        if event.action == "ADD":
            assert event.side is not None and event.price_ticks is not None and event.quantity is not None
            self._change_level(event.side, event.price_ticks, event.quantity, 1)
        else:
            assert existing is not None and event.quantity is not None
            self._change_level(existing.side, existing.price_ticks, -event.quantity,
                               -1 if event.quantity == existing.remaining else 0)
        self._apply_order_change(event, existing)
        top = self._current_top()
        ofi = _ofi(self._previous_top, top)
        self._previous_top = top if top[0] is not None and top[1] is not None else None
        self._last_sequence, self._last_timestamp = event.sequence, event.timestamp_ns
        self._events += 1
        return self._make_snapshot(event, self._bids, self._asks, top, ofi)


def replay(engine: BookEngine, events: list[BookEvent]) -> list[BookSnapshot]:
    return [engine.on_event(event) for event in events]
