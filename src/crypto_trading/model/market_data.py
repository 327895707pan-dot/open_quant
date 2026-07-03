from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class PositionDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass(frozen=True)
class Candle:
    symbol: str
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", self.symbol.upper())


@dataclass(frozen=True)
class PositionAdvice:
    direction: PositionDirection
    quantity: float
    stop_price: float | None = None

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.stop_price is not None and self.stop_price <= 0:
            raise ValueError("stop_price must be positive")


@dataclass(frozen=True)
class Signal:
    symbol: str
    action: SignalAction
    reason: str
    price: float | None = None
    advice: PositionAdvice | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", self.symbol.upper())

    @classmethod
    def hold(cls, symbol: str, reason: str) -> "Signal":
        return cls(symbol=symbol, action=SignalAction.HOLD, reason=reason)


def validate_candles(candles: Sequence[Candle]) -> None:
    previous_open_time: int | None = None
    for candle in candles:
        if not candle.symbol:
            raise ValueError("symbol is required")
        if candle.high < max(candle.open, candle.close, candle.low):
            raise ValueError("high must be greater than or equal to open, close, and low")
        if candle.low > min(candle.open, candle.close, candle.high):
            raise ValueError("low must be less than or equal to open, close, and high")
        if min(candle.open, candle.high, candle.low, candle.close) <= 0:
            raise ValueError("prices must be positive")
        if candle.volume < 0:
            raise ValueError("volume must be non-negative")
        if previous_open_time is not None and candle.open_time <= previous_open_time:
            raise ValueError("candles must be ordered by increasing open_time")
        previous_open_time = candle.open_time
