from crypto_trading.model.backtest import Backtester
from crypto_trading.model.market_data import Candle, PositionDirection
from crypto_trading.model.trend_model import TrendModel, TrendModelConfig


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


def make_model():
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


def test_empty_backtest_returns_zero_trade_result():
    result = Backtester(make_model()).run([])

    assert result.trade_count == 0
    assert result.net_pnl == 0
    assert result.trades == []


def test_backtest_records_reversal_and_final_close():
    candles = make_candles([10, 9, 8, 11, 14, 13, 10])

    result = Backtester(make_model()).run(candles)

    assert result.trade_count == 2

    first_trade, second_trade = result.trades
    assert first_trade.symbol == "BTCUSDT"
    assert first_trade.direction is PositionDirection.LONG
    assert first_trade.entry_time == 3
    assert first_trade.entry_price == 11
    assert first_trade.exit_time == 6
    assert first_trade.exit_price == 10
    assert first_trade.quantity > 0
    assert first_trade.pnl < 0

    assert second_trade.symbol == "BTCUSDT"
    assert second_trade.direction is PositionDirection.SHORT
    assert second_trade.entry_time == 6
    assert second_trade.entry_price == 10
    assert second_trade.exit_time == 6
    assert second_trade.exit_price == 10
    assert second_trade.quantity > 0
    assert second_trade.pnl == 0

    assert result.net_pnl == first_trade.pnl + second_trade.pnl
