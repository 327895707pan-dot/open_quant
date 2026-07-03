from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from crypto_trading.model.indicators import atr, ema, rsi
from crypto_trading.model.market_data import (
    Candle,
    PositionAdvice,
    PositionDirection,
    Signal,
    SignalAction,
    validate_candles,
)


@dataclass(frozen=True)
class TrendModelConfig:
    fast_ema_period: int = 12
    slow_ema_period: int = 26
    rsi_period: int = 14
    atr_period: int = 14
    rsi_long_ceiling: float = 70
    rsi_short_floor: float = 30
    risk_per_trade: float = 10
    atr_stop_multiple: float = 2

    def __post_init__(self) -> None:
        if self.fast_ema_period <= 0 or self.slow_ema_period <= 0:
            raise ValueError("EMA periods must be positive")
        if self.fast_ema_period >= self.slow_ema_period:
            raise ValueError("fast_ema_period must be less than slow_ema_period")
        if self.rsi_period <= 0 or self.atr_period <= 0:
            raise ValueError("RSI and ATR periods must be positive")
        if self.risk_per_trade <= 0:
            raise ValueError("risk_per_trade must be positive")
        if self.atr_stop_multiple <= 0:
            raise ValueError("atr_stop_multiple must be positive")


class TrendModel:
    def __init__(self, config: TrendModelConfig | None = None) -> None:
        self.config = config or TrendModelConfig()

    def generate_signal(
        self,
        candles: Sequence[Candle],
        current_position: PositionDirection = PositionDirection.FLAT,
    ) -> Signal:
        if not candles:
            return Signal.hold("UNKNOWN", "no candles")

        validate_candles(candles)
        symbol = candles[-1].symbol
        required = max(
            self.config.slow_ema_period,
            self.config.rsi_period + 1,
            self.config.atr_period,
        )
        if len(candles) < required + 1:
            return Signal.hold(symbol, "not enough candles")

        closes = [candle.close for candle in candles]
        fast = ema(closes, self.config.fast_ema_period)
        slow = ema(closes, self.config.slow_ema_period)
        rsi_values = rsi(closes, self.config.rsi_period)
        atr_values = atr(candles, self.config.atr_period)

        previous_fast = fast[-2]
        previous_slow = slow[-2]
        current_fast = fast[-1]
        current_slow = slow[-1]
        current_rsi = rsi_values[-1]
        current_atr = atr_values[-1]
        indicators = {
            previous_fast,
            previous_slow,
            current_fast,
            current_slow,
            current_rsi,
            current_atr,
        }
        if None in indicators:
            return Signal.hold(symbol, "indicators unavailable")

        price = candles[-1].close
        crossed_up = previous_fast <= previous_slow and current_fast > current_slow
        crossed_down = previous_fast >= previous_slow and current_fast < current_slow

        if crossed_up and current_rsi < self.config.rsi_long_ceiling:
            if current_position is PositionDirection.LONG:
                return Signal.hold(symbol, "already long")
            stop_price = price - (current_atr * self.config.atr_stop_multiple)
            quantity = self.config.risk_per_trade / max(price - stop_price, 1e-12)
            return Signal(
                symbol=symbol,
                action=SignalAction.BUY,
                reason="fast EMA crossed above slow EMA",
                price=price,
                advice=PositionAdvice(
                    direction=PositionDirection.LONG,
                    quantity=quantity,
                    stop_price=stop_price,
                ),
            )

        if crossed_down and current_rsi > self.config.rsi_short_floor:
            if current_position is PositionDirection.SHORT:
                return Signal.hold(symbol, "already short")
            stop_price = price + (current_atr * self.config.atr_stop_multiple)
            quantity = self.config.risk_per_trade / max(stop_price - price, 1e-12)
            return Signal(
                symbol=symbol,
                action=SignalAction.SELL,
                reason="fast EMA crossed below slow EMA",
                price=price,
                advice=PositionAdvice(
                    direction=PositionDirection.SHORT,
                    quantity=quantity,
                    stop_price=stop_price,
                ),
            )

        return Signal.hold(symbol, "no crossover")
