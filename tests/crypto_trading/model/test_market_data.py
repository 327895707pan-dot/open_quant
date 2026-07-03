import pytest

from crypto_trading.model.market_data import (
    Candle,
    PositionAdvice,
    PositionDirection,
    Signal,
    SignalAction,
    validate_candles,
)


def test_valid_candle_passes_validation():
    candle = Candle(
        symbol="btcusdt",
        open_time=1,
        open=100,
        high=110,
        low=95,
        close=105,
        volume=12.5,
    )

    validate_candles([candle])

    assert candle.symbol == "BTCUSDT"


def test_invalid_candle_price_raises():
    candle = Candle(
        symbol="BTCUSDT",
        open_time=1,
        open=100,
        high=90,
        low=95,
        close=105,
        volume=1,
    )

    with pytest.raises(ValueError, match="high must be"):
        validate_candles([candle])


def test_candle_rejects_malformed_symbol():
    with pytest.raises(ValueError, match="symbol"):
        Candle(
            symbol="",
            open_time=1,
            open=100,
            high=110,
            low=95,
            close=105,
            volume=1,
        )


def test_candle_rejects_malformed_price_input():
    with pytest.raises(ValueError, match="high must be a real number"):
        Candle(
            symbol="BTCUSDT",
            open_time=1,
            open=100,
            high="110",
            low=95,
            close=105,
            volume=1,
        )


def test_signal_defaults_to_hold_without_advice():
    signal = Signal.hold("BTCUSDT", reason="not enough data")

    assert signal.action is SignalAction.HOLD
    assert signal.symbol == "BTCUSDT"
    assert signal.reason == "not enough data"
    assert signal.advice is None


def test_signal_rejects_non_positive_price():
    with pytest.raises(ValueError, match="price must be positive"):
        Signal(
            symbol="BTCUSDT",
            action=SignalAction.BUY,
            reason="entry",
            price=0,
        )


def test_position_advice_requires_positive_quantity():
    with pytest.raises(ValueError, match="quantity"):
        PositionAdvice(direction=PositionDirection.LONG, quantity=0, stop_price=99)
