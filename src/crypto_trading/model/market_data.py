from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from numbers import Integral, Real
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
        object.__setattr__(self, "symbol", _normalize_symbol(self.symbol))
        object.__setattr__(self, "open_time", _validate_open_time(self.open_time))
        object.__setattr__(self, "open", _validate_price("open", self.open))
        object.__setattr__(self, "high", _validate_price("high", self.high))
        object.__setattr__(self, "low", _validate_price("low", self.low))
        object.__setattr__(self, "close", _validate_price("close", self.close))
        object.__setattr__(self, "volume", _validate_non_negative_price("volume", self.volume))


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
        object.__setattr__(self, "symbol", _normalize_symbol(self.symbol))
        if self.price is not None:
            object.__setattr__(self, "price", _validate_positive_price("price", self.price))

    @classmethod
    def hold(cls, symbol: str, reason: str) -> "Signal":
        return cls(symbol=symbol, action=SignalAction.HOLD, reason=reason)


def validate_candles(candles: Sequence[Candle]) -> None:
    previous_open_time: int | None = None
    for candle in candles:
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


def _normalize_symbol(symbol: object) -> str:
    if not isinstance(symbol, str):
        raise ValueError("symbol must be a non-empty string")
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol must be a non-empty string")
    return normalized


def _validate_open_time(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError("open_time must be an integer")
    return int(value)


def _validate_price(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a real number")
    numeric = float(value)
    if not isfinite(numeric):
        raise ValueError(f"{name} must be finite")
    return numeric


def _validate_non_negative_price(name: str, value: object) -> float:
    numeric = _validate_price(name, value)
    if numeric < 0:
        raise ValueError(f"{name} must be non-negative")
    return numeric


def _validate_positive_price(name: str, value: object) -> float:
    numeric = _validate_price(name, value)
    if numeric <= 0:
        raise ValueError(f"{name} must be positive")
    return numeric
