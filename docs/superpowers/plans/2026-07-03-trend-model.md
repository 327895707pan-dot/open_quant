# Trend Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic EMA/RSI/ATR trend model with offline backtesting and dry-run strategy integration.

**Architecture:** Add a `crypto_trading.model` package that is independent from Binance, storage, and network code. The model exposes plain dataclasses and pure functions first, then a thin strategy adapter connects signals to the existing `OrderManager` and `RiskManager`.

**Tech Stack:** Python 3.12, dataclasses, pytest, pytest-asyncio, existing `crypto_trading` package structure.

## Global Constraints

- The model package has no network dependency.
- The first strategy adapter does not submit real orders by default.
- Existing event parsing, state, risk, and storage tests continue to pass.
- Avoid machine learning, grid trading, martingale logic, and unlimited averaging.
- Empty candle input returns a `HOLD` signal and does not raise.
- Non-positive prices or malformed candles raise `ValueError` at the model boundary.
- Indicator functions reject invalid periods with `ValueError`.

---

## File Structure

- Create `src/crypto_trading/model/__init__.py`: public exports for model primitives.
- Create `src/crypto_trading/model/market_data.py`: `Candle`, `Signal`, `PositionAdvice`, enums, and validation helpers.
- Create `src/crypto_trading/model/indicators.py`: pure `ema`, `rsi`, and `atr` functions.
- Create `src/crypto_trading/model/trend_model.py`: configurable trend model and signal generation rules.
- Create `src/crypto_trading/model/backtest.py`: one-position-at-a-time deterministic backtester.
- Create `src/crypto_trading/strategy/trend_strategy.py`: dry-run strategy adapter around `TrendModel`.
- Modify `README.md`: document model test and minimal backtest usage.
- Add tests under `tests/crypto_trading/model/` and `tests/crypto_trading/test_trend_strategy.py`.

---

### Task 1: Market Data Types

**Files:**
- Create: `src/crypto_trading/model/__init__.py`
- Create: `src/crypto_trading/model/market_data.py`
- Test: `tests/crypto_trading/model/test_market_data.py`

**Interfaces:**
- Produces: `SignalAction`, `PositionDirection`, `Candle`, `PositionAdvice`, `Signal`, `validate_candles(candles: Sequence[Candle]) -> None`
- Consumes: No project-local interfaces.

- [ ] **Step 1: Write the failing test**

```python
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


def test_signal_defaults_to_hold_without_advice():
    signal = Signal.hold("BTCUSDT", reason="not enough data")

    assert signal.action is SignalAction.HOLD
    assert signal.symbol == "BTCUSDT"
    assert signal.reason == "not enough data"
    assert signal.advice is None


def test_position_advice_requires_positive_quantity():
    with pytest.raises(ValueError, match="quantity"):
        PositionAdvice(direction=PositionDirection.LONG, quantity=0, stop_price=99)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/crypto_trading/model/test_market_data.py -q`

Expected: FAIL because `crypto_trading.model` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `src/crypto_trading/model/market_data.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
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
        object.__setattr__(self, "symbol", self.symbol.upper())


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
        object.__setattr__(self, "symbol", self.symbol.upper())

    @classmethod
    def hold(cls, symbol: str, reason: str) -> "Signal":
        return cls(symbol=symbol, action=SignalAction.HOLD, reason=reason)


def validate_candles(candles: Sequence[Candle]) -> None:
    previous_open_time: int | None = None
    for candle in candles:
        if not candle.symbol:
            raise ValueError("symbol is required")
        if min(candle.open, candle.high, candle.low, candle.close) <= 0:
            raise ValueError("prices must be positive")
        if candle.volume < 0:
            raise ValueError("volume must be non-negative")
        if candle.high < max(candle.open, candle.close, candle.low):
            raise ValueError("high must be greater than or equal to open, close, and low")
        if candle.low > min(candle.open, candle.close, candle.high):
            raise ValueError("low must be less than or equal to open, close, and high")
        if previous_open_time is not None and candle.open_time <= previous_open_time:
            raise ValueError("candles must be ordered by increasing open_time")
        previous_open_time = candle.open_time
```

Create `src/crypto_trading/model/__init__.py`:

```python
from crypto_trading.model.market_data import (
    Candle,
    PositionAdvice,
    PositionDirection,
    Signal,
    SignalAction,
    validate_candles,
)

__all__ = [
    "Candle",
    "PositionAdvice",
    "PositionDirection",
    "Signal",
    "SignalAction",
    "validate_candles",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/crypto_trading/model/test_market_data.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/crypto_trading/model/__init__.py src/crypto_trading/model/market_data.py tests/crypto_trading/model/test_market_data.py
git commit -m "feat: add market data model types"
```

---

### Task 2: Indicator Functions

**Files:**
- Create: `src/crypto_trading/model/indicators.py`
- Test: `tests/crypto_trading/model/test_indicators.py`

**Interfaces:**
- Consumes: `Candle`
- Produces: `ema(values: Sequence[float], period: int) -> list[float | None]`, `rsi(values: Sequence[float], period: int) -> list[float | None]`, `atr(candles: Sequence[Candle], period: int) -> list[float | None]`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/crypto_trading/model/test_indicators.py -q`

Expected: FAIL because `crypto_trading.model.indicators` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `src/crypto_trading/model/indicators.py`:

```python
from __future__ import annotations

from typing import Sequence

from crypto_trading.model.market_data import Candle, validate_candles


def _validate_period(period: int) -> None:
    if period <= 0:
        raise ValueError("period must be positive")


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/crypto_trading/model/test_indicators.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/crypto_trading/model/indicators.py tests/crypto_trading/model/test_indicators.py
git commit -m "feat: add trend model indicators"
```

---

### Task 3: Trend Model Rules

**Files:**
- Create: `src/crypto_trading/model/trend_model.py`
- Modify: `src/crypto_trading/model/__init__.py`
- Test: `tests/crypto_trading/model/test_trend_model.py`

**Interfaces:**
- Consumes: `Candle`, `PositionDirection`, `Signal`, `SignalAction`, `PositionAdvice`, `ema`, `rsi`, `atr`
- Produces: `TrendModelConfig`, `TrendModel.generate_signal(candles: Sequence[Candle], current_position: PositionDirection = PositionDirection.FLAT) -> Signal`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/crypto_trading/model/test_trend_model.py -q`

Expected: FAIL because `crypto_trading.model.trend_model` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `src/crypto_trading/model/trend_model.py`:

```python
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
        if None in {previous_fast, previous_slow, current_fast, current_slow, current_rsi, current_atr}:
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
                advice=PositionAdvice(PositionDirection.LONG, quantity, stop_price),
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
                advice=PositionAdvice(PositionDirection.SHORT, quantity, stop_price),
            )
        return Signal.hold(symbol, "no crossover")
```

Modify `src/crypto_trading/model/__init__.py`:

```python
from crypto_trading.model.market_data import (
    Candle,
    PositionAdvice,
    PositionDirection,
    Signal,
    SignalAction,
    validate_candles,
)
from crypto_trading.model.trend_model import TrendModel, TrendModelConfig

__all__ = [
    "Candle",
    "PositionAdvice",
    "PositionDirection",
    "Signal",
    "SignalAction",
    "TrendModel",
    "TrendModelConfig",
    "validate_candles",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/crypto_trading/model/test_trend_model.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/crypto_trading/model/__init__.py src/crypto_trading/model/trend_model.py tests/crypto_trading/model/test_trend_model.py
git commit -m "feat: add deterministic trend model"
```

---

### Task 4: Offline Backtester

**Files:**
- Create: `src/crypto_trading/model/backtest.py`
- Test: `tests/crypto_trading/model/test_backtest.py`

**Interfaces:**
- Consumes: `Candle`, `PositionDirection`, `SignalAction`, `TrendModel`
- Produces: `BacktestTrade`, `BacktestResult`, `Backtester.run(candles: Sequence[Candle]) -> BacktestResult`

- [ ] **Step 1: Write the failing test**

```python
from crypto_trading.model.backtest import Backtester
from crypto_trading.model.market_data import Candle
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


def test_empty_backtest_returns_zero_trade_result():
    result = Backtester(TrendModel()).run([])

    assert result.trade_count == 0
    assert result.net_pnl == 0
    assert result.trades == []


def test_backtest_records_trade_when_signal_appears():
    model = TrendModel(
        TrendModelConfig(
            fast_ema_period=2,
            slow_ema_period=3,
            rsi_period=2,
            atr_period=2,
            risk_per_trade=10,
            atr_stop_multiple=2,
        )
    )
    result = Backtester(model).run(make_candles([10, 9, 8, 11, 14, 13, 10]))

    assert result.trade_count >= 1
    assert result.trades[0].symbol == "BTCUSDT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/crypto_trading/model/test_backtest.py -q`

Expected: FAIL because `crypto_trading.model.backtest` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `src/crypto_trading/model/backtest.py`:

```python
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
            signal = self.model.generate_signal(window, current_position=current_position)
            candle = window[-1]
            if signal.action is SignalAction.BUY and signal.advice:
                if open_trade and open_trade.direction is PositionDirection.SHORT:
                    trades.append(_close_trade(open_trade, candle.open_time, candle.close))
                open_trade = BacktestTrade(
                    symbol=candle.symbol,
                    direction=PositionDirection.LONG,
                    entry_time=candle.open_time,
                    entry_price=candle.close,
                    quantity=signal.advice.quantity,
                )
                current_position = PositionDirection.LONG
            elif signal.action is SignalAction.SELL and signal.advice:
                if open_trade and open_trade.direction is PositionDirection.LONG:
                    trades.append(_close_trade(open_trade, candle.open_time, candle.close))
                open_trade = BacktestTrade(
                    symbol=candle.symbol,
                    direction=PositionDirection.SHORT,
                    entry_time=candle.open_time,
                    entry_price=candle.close,
                    quantity=signal.advice.quantity,
                )
                current_position = PositionDirection.SHORT

        if open_trade is not None:
            trades.append(_close_trade(open_trade, candles[-1].open_time, candles[-1].close))
        return BacktestResult(trades=trades, net_pnl=sum(trade.pnl for trade in trades))


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/crypto_trading/model/test_backtest.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/crypto_trading/model/backtest.py tests/crypto_trading/model/test_backtest.py
git commit -m "feat: add offline trend model backtester"
```

---

### Task 5: Dry-Run Strategy Adapter And Docs

**Files:**
- Create: `src/crypto_trading/strategy/trend_strategy.py`
- Modify: `README.md`
- Test: `tests/crypto_trading/test_trend_strategy.py`

**Interfaces:**
- Consumes: `BaseStrategy`, `OrderManager`, `TrendModel`, `Candle`, `SignalAction`
- Produces: `TrendStrategy.add_candle(candle: Candle) -> None`, `TrendStrategy.on_timer() -> None`

- [ ] **Step 1: Write the failing test**

```python
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
            open_time=i,
            open=close - 1,
            high=close + 2,
            low=close - 2,
            close=close,
            volume=1,
        )
        for i, close in enumerate(closes)
    ]


def model():
    return TrendModel(
        TrendModelConfig(
            fast_ema_period=2,
            slow_ema_period=3,
            rsi_period=2,
            atr_period=2,
            risk_per_trade=10,
            atr_stop_multiple=2,
        )
    )


@pytest.mark.asyncio
async def test_trend_strategy_does_not_trade_when_disabled():
    strategy = TrendStrategy(["BTCUSDT"], model=model(), enable_trading=False)
    manager = RecordingOrderManager()
    strategy.set_order_manager(manager)
    for candle in make_candles([10, 9, 8, 11, 14]):
        strategy.add_candle(candle)

    await strategy.on_timer()

    assert manager.market_orders == []


@pytest.mark.asyncio
async def test_trend_strategy_routes_enabled_signal_to_order_manager():
    strategy = TrendStrategy(["BTCUSDT"], model=model(), enable_trading=True)
    manager = RecordingOrderManager()
    strategy.set_order_manager(manager)
    for candle in make_candles([10, 9, 8, 11, 14]):
        strategy.add_candle(candle)

    await strategy.on_timer()

    assert manager.market_orders
    assert manager.market_orders[0]["symbol"] == "BTCUSDT"
    assert manager.market_orders[0]["side"] == "BUY"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/crypto_trading/test_trend_strategy.py -q`

Expected: FAIL because `TrendStrategy` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `src/crypto_trading/strategy/trend_strategy.py`:

```python
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
```

Modify `README.md` by adding:

```markdown
## Trend Model

The first real model is a deterministic EMA/RSI/ATR trend model. It can be
tested without Binance credentials:

```bash
pytest tests/crypto_trading/model -q
```

The model package is offline-only. `TrendStrategy` adapts model signals to the
existing order flow, but trading remains disabled unless the strategy is created
with `enable_trading=True`, and all orders still pass through `RiskManager`.
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/crypto_trading/model tests/crypto_trading/test_trend_strategy.py -q
pytest tests/crypto_trading -q
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/crypto_trading/strategy/trend_strategy.py README.md tests/crypto_trading/test_trend_strategy.py
git commit -m "feat: add dry-run trend strategy adapter"
```

---

## Self-Review

- Spec coverage: Tasks 1-3 implement model data, indicators, and trend rules. Task 4 implements offline backtesting. Task 5 implements dry-run strategy integration and README documentation.
- Red-flag scan: This plan does not include unresolved markers or deferred implementation notes.
- Type consistency: `Candle`, `PositionDirection`, `SignalAction`, `TrendModel`, and `TrendModelConfig` are introduced before downstream tasks use them.
- Scope check: The plan excludes live kline ingestion, exchange downloads, machine learning, real-money execution, grid trading, and martingale behavior as required by the spec.
