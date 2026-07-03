from __future__ import annotations

import logging

from crypto_trading.model.market_data import Candle, PositionDirection, SignalAction
from crypto_trading.model.trend_model import TrendModel
from crypto_trading.strategy.base import BaseStrategy

logger = logging.getLogger(__name__)


class TrendStrategy(BaseStrategy):
    name = "trend_strategy"

    def __init__(
        self,
        symbols: list[str],
        *,
        model: TrendModel | None = None,
        enable_trading: bool = False,
    ) -> None:
        super().__init__(symbols)
        self.model = model or TrendModel()
        self.enable_trading = enable_trading
        self._candles: dict[str, list[Candle]] = {symbol.upper(): [] for symbol in symbols}
        self._positions: dict[str, PositionDirection] = {
            symbol.upper(): PositionDirection.FLAT for symbol in symbols
        }

    def add_candle(self, candle: Candle) -> None:
        symbol = candle.symbol.upper()
        if symbol not in self._candles:
            logger.info("Ignoring candle for unsupported symbol %s", symbol)
            return
        self._candles[symbol].append(candle)

    async def on_timer(self) -> None:
        if not self.enable_trading:
            return
        if self.order_manager is None:
            logger.warning("Trend trading enabled but order manager is not configured")
            return

        for symbol, candles in self._candles.items():
            signal = self.model.generate_signal(
                candles,
                current_position=self._positions.get(symbol, PositionDirection.FLAT),
            )
            if signal.action is SignalAction.HOLD or signal.advice is None:
                continue

            side = "BUY" if signal.action is SignalAction.BUY else "SELL"
            await self.order_manager.create_market_order(
                symbol=symbol,
                side=side,
                quantity=signal.advice.quantity,
            )
            self._positions[symbol] = signal.advice.direction
