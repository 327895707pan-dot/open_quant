# Trend Model Design

## Purpose

Build the first real quantitative model for `open_quant` as a deterministic,
offline-testable trend-following model. The model must produce trading signals
from OHLCV candles without requiring Binance credentials, and it must remain
dry-run by default when connected to the existing execution path.

This design intentionally avoids machine learning, grid trading, martingale
logic, and direct live trading automation. The first goal is a model that can be
tested, backtested, and inspected before any real order flow is enabled.

## Scope

The first implementation adds:

- Standard candle and signal data structures.
- EMA, RSI, and ATR indicators implemented with deterministic pure functions.
- A trend model that combines EMA crossover, RSI filters, and ATR-based risk
  sizing.
- A lightweight offline backtester for validating signal behavior on historical
  candles.
- A dry-run strategy adapter that can use the model through the existing
  `OrderManager` and `RiskManager`.

Out of scope:

- Live kline WebSocket ingestion.
- Exchange historical data download.
- Machine learning training or inference.
- Real-money order submission.
- Grid, martingale, or unlimited averaging strategies.

## Architecture

New package:

```text
src/crypto_trading/model/
  __init__.py
  market_data.py
  indicators.py
  trend_model.py
  backtest.py
```

New strategy adapter:

```text
src/crypto_trading/strategy/trend_strategy.py
```

`market_data.py` defines plain dataclasses for `Candle`, `Signal`, and
`PositionAdvice`. These types keep the model independent from Binance-specific
payloads and from the execution layer.

`indicators.py` contains pure indicator functions. The functions accept numeric
series or candles and return lists aligned to the input length, using `None`
where there is not enough lookback data.

`trend_model.py` owns the trading rules. It receives a list of candles and an
optional current position snapshot, then returns a `Signal`. It does not place
orders and does not access network or storage.

`backtest.py` runs the model over historical candles, simulates one position at
a time, and returns summary metrics plus a trade list. It is intentionally small
and deterministic so the model can be validated before adding richer execution
simulation.

`trend_strategy.py` adapts model signals to `OrderManager` calls. It must keep
trading disabled by default and continue to rely on `RiskManager` for final
approval.

## Model Rules

Inputs:

- Symbol.
- Ordered OHLCV candles.
- Fast EMA period, slow EMA period, RSI period, ATR period.
- RSI long ceiling and RSI short floor.
- Risk per trade and ATR stop multiple.
- Optional current position direction and size.

Signal rules:

- Return `HOLD` if there are not enough candles for all indicators.
- Return `BUY` when fast EMA crosses above slow EMA and RSI is below the long
  ceiling.
- Return `SELL` when fast EMA crosses below slow EMA and RSI is above the short
  floor.
- Return `HOLD` when the signal direction matches an existing open position.
- Include an ATR-derived stop price when ATR is available.
- Include position advice sized from configured risk and stop distance when
  enough information is available.

The model should use conservative defaults:

- `fast_ema_period = 12`
- `slow_ema_period = 26`
- `rsi_period = 14`
- `atr_period = 14`
- `rsi_long_ceiling = 70`
- `rsi_short_floor = 30`
- `atr_stop_multiple = 2`

## Data Flow

```text
Historical candles
    -> indicators
    -> TrendModel.generate_signal
    -> Backtester or TrendStrategy
    -> OrderManager
    -> RiskManager
    -> dry-run order response
```

The model remains usable without live Binance credentials. Any future live
integration should translate exchange klines into `Candle` first, then pass
those candles into the same model API.

## Error Handling

- Empty candle input returns a `HOLD` signal and does not raise.
- Non-positive prices or malformed candles raise `ValueError` at the model
  boundary.
- Indicator functions should reject invalid periods with `ValueError`.
- Backtest should return zero-trade results for insufficient candle history.
- Strategy adapter should log rejected or skipped signals without retry loops.

## Testing

Tests should cover:

- EMA, RSI, and ATR calculations on small deterministic series.
- Indicator behavior when lookback data is insufficient.
- Trend model `BUY`, `SELL`, and `HOLD` decisions.
- No duplicate open signal when current position already matches direction.
- Backtest behavior for empty, insufficient, rising, and falling candle sets.
- Strategy adapter using `OrderManager` in dry-run without bypassing
  `RiskManager`.

## Acceptance Criteria

- `pytest tests/crypto_trading -q` passes.
- The model package has no network dependency.
- The first strategy adapter does not submit real orders by default.
- Existing event parsing, state, risk, and storage tests continue to pass.
- The README or docs explain how to run the model tests and a minimal backtest.
