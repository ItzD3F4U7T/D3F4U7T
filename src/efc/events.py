"""Ordered event definitions for the offline EFC prototype."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TradeEvent:
    """A trade-price observation represented in integer ticks."""
    sequence: int
    price_ticks: int

    def __post_init__(self) -> None:
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise TypeError("sequence must be an integer")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        if isinstance(self.price_ticks, bool) or not isinstance(self.price_ticks, int):
            raise TypeError("price_ticks must be an integer")
        if self.price_ticks <= 0:
            raise ValueError("price_ticks must be positive")
