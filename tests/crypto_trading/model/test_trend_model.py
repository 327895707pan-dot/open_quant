from crypto_trading.model.market_data import Candle, PositionDirection, SignalAction
from crypto_trading.model.trend_model import TrendModel, TrendModelConfig


def make_candles(closes):
    return [
        Candle(
            symbol="BTCUSDT",
            open_time=i,
            open=close - 1,
            high=close + 2,
            low=close - 2,
            close=close,
            volume=1,
        )
        for i, close in enumerate(closes)
    ]


def config():
    return TrendModelConfig(
        fast_ema_period=2,
        slow_ema_period=3,
        rsi_period=2,
        atr_period=2,
        rsi_long_ceiling=100,
        rsi_short_floor=0,
        risk_per_trade=10,
        atr_stop_multiple=2,
    )


def test_empty_input_holds():
    signal = TrendModel(config()).generate_signal([])

    assert signal.action is SignalAction.HOLD
    assert "no candles" in signal.reason


def test_buy_signal_on_fast_cross_above_slow():
    candles = make_candles([10, 9, 8, 11, 14])

    signal = TrendModel(config()).generate_signal(candles)

    assert signal.action is SignalAction.BUY
    assert signal.advice is not None
    assert signal.advice.direction is PositionDirection.LONG
    assert signal.advice.quantity > 0
    assert signal.advice.stop_price < candles[-1].close


def test_sell_signal_on_fast_cross_below_slow():
    candles = make_candles([10, 11, 12, 9, 6])

    signal = TrendModel(config()).generate_signal(candles)

    assert signal.action is SignalAction.SELL
    assert signal.advice is not None
    assert signal.advice.direction is PositionDirection.SHORT
    assert signal.advice.stop_price > candles[-1].close


def test_matching_existing_position_holds():
    candles = make_candles([10, 9, 8, 11, 14])

    signal = TrendModel(config()).generate_signal(
        candles,
        current_position=PositionDirection.LONG,
    )

    assert signal.action is SignalAction.HOLD
    assert "already long" in signal.reason


def test_rsi_filter_blocks_overheated_long_signal():
    candles = make_candles([10, 9, 8, 11, 14])
    strict_config = TrendModelConfig(
        fast_ema_period=2,
        slow_ema_period=3,
        rsi_period=2,
        atr_period=2,
        rsi_long_ceiling=50,
        rsi_short_floor=0,
        risk_per_trade=10,
        atr_stop_multiple=2,
    )

    signal = TrendModel(strict_config).generate_signal(candles)

    assert signal.action is SignalAction.HOLD
