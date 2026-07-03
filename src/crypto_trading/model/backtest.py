from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from crypto_trading.model.market_data import Candle, PositionDirection, SignalAction
from crypto_trading.model.trend_model import TrendModel


@dataclass(frozen=True)
class BacktestTrade:
    symbol: str
    direction: PositionDirection
    entry_time: int
    entry_price: float
    exit_time: int | None = None
    exit_price: float | None = None
    quantity: float = 0.0
    pnl: float = 0.0


@dataclass(frozen=True)
class BacktestResult:
    trades: list[BacktestTrade]
    net_pnl: float

    @property
    def trade_count(self) -> int:
        return len(self.trades)


class Backtester:
    def __init__(self, model: TrendModel) -> None:
        self.model = model

    def run(self, candles: Sequence[Candle]) -> BacktestResult:
        if not candles:
            return BacktestResult(trades=[], net_pnl=0.0)

        trades: list[BacktestTrade] = []
        open_trade: BacktestTrade | None = None
        current_position = PositionDirection.FLAT

        for index in range(1, len(candles) + 1):
            window = candles[:index]
            candle = window[-1]
            signal = self.model.generate_signal(window, current_position=current_position)

            if signal.action is SignalAction.BUY and signal.advice is not None:
                if open_trade is not None and open_trade.direction is PositionDirection.SHORT:
                    trades.append(
                        _close_trade(
                            open_trade,
                            exit_time=candle.open_time,
                            exit_price=candle.close,
                        )
                    )
                open_trade = BacktestTrade(
                    symbol=candle.symbol,
                    direction=PositionDirection.LONG,
                    entry_time=candle.open_time,
                    entry_price=candle.close,
                    quantity=signal.advice.quantity,
                )
                current_position = PositionDirection.LONG
            elif signal.action is SignalAction.SELL and signal.advice is not None:
                if open_trade is not None and open_trade.direction is PositionDirection.LONG:
                    trades.append(
                        _close_trade(
                            open_trade,
                            exit_time=candle.open_time,
                            exit_price=candle.close,
                        )
                    )
                open_trade = BacktestTrade(
                    symbol=candle.symbol,
                    direction=PositionDirection.SHORT,
                    entry_time=candle.open_time,
                    entry_price=candle.close,
                    quantity=signal.advice.quantity,
                )
                current_position = PositionDirection.SHORT

        if open_trade is not None:
            final_candle = candles[-1]
            trades.append(
                _close_trade(
                    open_trade,
                    exit_time=final_candle.open_time,
                    exit_price=final_candle.close,
                )
            )

        return BacktestResult(
            trades=trades,
            net_pnl=sum(trade.pnl for trade in trades),
        )


def _close_trade(trade: BacktestTrade, exit_time: int, exit_price: float) -> BacktestTrade:
    if trade.direction is PositionDirection.LONG:
        pnl = (exit_price - trade.entry_price) * trade.quantity
    else:
        pnl = (trade.entry_price - exit_price) * trade.quantity

    return BacktestTrade(
        symbol=trade.symbol,
        direction=trade.direction,
        entry_time=trade.entry_time,
        entry_price=trade.entry_price,
        exit_time=exit_time,
        exit_price=exit_price,
        quantity=trade.quantity,
        pnl=pnl,
    )
