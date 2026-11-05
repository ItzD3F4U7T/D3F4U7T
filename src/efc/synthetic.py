"""Deterministic synthetic event generation for repeatable experiments."""
from __future__ import annotations
import random
from collections.abc import Iterator
from .events import TradeEvent


def generate_events(count: int, *, seed: int = 20261105,
                    start_price_ticks: int = 100_000) -> Iterator[TradeEvent]:
    """Yield synthetic random-walk prices; these are not historical market data."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("count must be an integer")
    if count < 0:
        raise ValueError("count must be non-negative")
    if isinstance(start_price_ticks, bool) or not isinstance(start_price_ticks, int):
        raise TypeError("start_price_ticks must be an integer")
    if start_price_ticks <= 0:
        raise ValueError("start_price_ticks must be positive")
    rng = random.Random(seed)
    price = start_price_ticks
    for sequence in range(count):
        price = max(1, price + rng.randint(-3, 3))
        yield TradeEvent(sequence, price)
