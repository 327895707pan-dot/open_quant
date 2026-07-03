import pytest

from crypto_trading.model.market_data import Candle
from crypto_trading.model.trend_model import TrendModel, TrendModelConfig
from crypto_trading.strategy.trend_strategy import TrendStrategy


class RecordingOrderManager:
    def __init__(self):
        self.market_orders = []

    async def create_market_order(self, **kwargs):
        self.market_orders.append(kwargs)
        return {"dry_run": True, "request": kwargs}


def make_candles(closes):
    return [
        Candle(
            symbol="BTCUSDT",
            open_time=index,
            open=close - 1,
            high=close + 2,
            low=close - 2,
            close=close,
            volume=1,
        )
        for index, close in enumerate(closes)
    ]


def model():
    return TrendModel(
        TrendModelConfig(
            fast_ema_period=2,
            slow_ema_period=3,
            rsi_period=2,
            atr_period=2,
            rsi_long_ceiling=100,
            rsi_short_floor=0,
            risk_per_trade=10,
            atr_stop_multiple=2,
        )
    )


@pytest.mark.asyncio
async def test_trend_strategy_does_not_trade_when_disabled():
    strategy = TrendStrategy(["BTCUSDT"], model=model(), enable_trading=False)
    manager = RecordingOrderManager()
    strategy.set_order_manager(manager)
    for candle in make_candles([10, 9, 8, 9, 12]):
        strategy.add_candle(candle)

    await strategy.on_timer()

    assert manager.market_orders == []


@pytest.mark.asyncio
async def test_trend_strategy_routes_enabled_signal_to_order_manager():
    strategy = TrendStrategy(["BTCUSDT"], model=model(), enable_trading=True)
    manager = RecordingOrderManager()
    strategy.set_order_manager(manager)
    for candle in make_candles([10, 9, 8, 9, 12]):
        strategy.add_candle(candle)

    await strategy.on_timer()

    assert manager.market_orders
    assert manager.market_orders[0]["symbol"] == "BTCUSDT"
    assert manager.market_orders[0]["side"] == "BUY"
