from __future__ import annotations

from typing import Sequence

from crypto_trading.model.market_data import Candle, validate_candles


def _validate_period(period: int) -> None:
    if isinstance(period, bool) or not isinstance(period, int):
        raise ValueError("period must be a positive integer")
    if period <= 0:
        raise ValueError("period must be a positive integer")


def ema(values: Sequence[float], period: int) -> list[float | None]:
    _validate_period(period)
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result

    multiplier = 2 / (period + 1)
    current = sum(values[:period]) / period
    result[period - 1] = current

    for index in range(period, len(values)):
        current = (values[index] - current) * multiplier + current
        result[index] = current

    return result


def rsi(values: Sequence[float], period: int) -> list[float | None]:
    _validate_period(period)
    result: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return result

    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    result[period] = _rsi_value(average_gain, average_loss)

    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0)
        loss = abs(min(change, 0))
        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period
        result[index] = _rsi_value(average_gain, average_loss)

    return result


def atr(candles: Sequence[Candle], period: int) -> list[float | None]:
    _validate_period(period)
    validate_candles(candles)

    result: list[float | None] = [None] * len(candles)
    if len(candles) < period:
        return result

    true_ranges: list[float] = []
    previous_close: float | None = None
    for candle in candles:
        if previous_close is None:
            true_range = candle.high - candle.low
        else:
            true_range = max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        true_ranges.append(true_range)
        previous_close = candle.close

    current = sum(true_ranges[:period]) / period
    result[period - 1] = current

    for index in range(period, len(candles)):
        current = ((current * (period - 1)) + true_ranges[index]) / period
        result[index] = current

    return result


def _rsi_value(average_gain: float, average_loss: float) -> float:
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))
