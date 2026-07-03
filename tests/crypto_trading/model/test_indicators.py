import pytest

from crypto_trading.model.indicators import atr, ema, rsi
from crypto_trading.model.market_data import Candle


def candles_from_closes(closes):
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


def test_ema_returns_none_until_seed_period():
    result = ema([10, 11, 12, 13], period=3)

    assert result[0] is None
    assert result[1] is None
    assert result[2] == pytest.approx(11)
    assert result[3] == pytest.approx(12)


def test_rsi_rising_series_reaches_high_value():
    result = rsi([1, 2, 3, 4, 5, 6], period=3)

    assert result[-1] == pytest.approx(100)


def test_atr_uses_true_range_and_period_average():
    result = atr(candles_from_closes([10, 12, 11, 15]), period=3)

    assert result[0] is None
    assert result[1] is None
    assert result[2] == pytest.approx(4)
    assert result[3] == pytest.approx(4.6666666667)


@pytest.mark.parametrize("period", [0, -1])
def test_indicators_reject_invalid_period(period):
    with pytest.raises(ValueError, match="period"):
        ema([1, 2, 3], period)


@pytest.mark.parametrize("period", [True, 3.5, 3.0])
def test_indicators_reject_non_integer_period(period):
    with pytest.raises(ValueError, match="period"):
        ema([1, 2, 3], period)
