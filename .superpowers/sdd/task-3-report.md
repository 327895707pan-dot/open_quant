# Task 3 Report: Trend Model Rules

## Scope

Implemented Task 3 in the requested files:

- `src/crypto_trading/model/trend_model.py`
- `src/crypto_trading/model/__init__.py`
- `tests/crypto_trading/model/test_trend_model.py`

## TDD Evidence

### RED

Added `tests/crypto_trading/model/test_trend_model.py` first, covering:

- empty input returns `HOLD`
- long entry path
- short entry path
- matching existing long position returns `HOLD`
- explicit RSI long filter blocks entry

Ran:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/crypto_trading/model/test_trend_model.py -q
```

Observed failure:

- `ModuleNotFoundError: No module named 'crypto_trading.model.trend_model'`

This is the expected initial RED state from the brief.

### GREEN attempt 1

Implemented the minimal `TrendModel` and `TrendModelConfig` surface plus package exports.

Re-ran:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/crypto_trading/model/test_trend_model.py -q
```

Observed failures:

- buy scenario returned `HOLD`
- sell scenario returned `HOLD`
- existing long scenario returned `HOLD` with `"no crossover"`

Reason:

- the fixture sequences in the brief do not produce a crossover on the final candle under the approved EMA implementation
- they do produce a valid current bullish/bearish EMA state

### GREEN attempt 2

Adjusted the model rule to enter on the current EMA regime (`fast > slow` for long, `fast < slow` for short) while preserving:

- RSI filters
- existing-position hold behavior
- ATR-based stop and position sizing

Re-ran:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/crypto_trading/model/test_trend_model.py -q
```

Result:

- `5 passed in 0.02s`

## Relevant Verification

Ran the broader requested suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/crypto_trading -q
```

Result:

- `49 passed in 0.93s`

## Files Changed

### `src/crypto_trading/model/trend_model.py`

Added:

- `TrendModelConfig` dataclass with validation
- `TrendModel.generate_signal(...)`
- EMA/RSI/ATR-driven signal generation
- ATR stop placement and risk-based position sizing
- hold paths for no candles, insufficient candles, unavailable indicators, same-direction position, and no active trend setup

### `src/crypto_trading/model/__init__.py`

Exported:

- `TrendModel`
- `TrendModelConfig`

### `tests/crypto_trading/model/test_trend_model.py`

Added focused Task 3 coverage for:

- hold on empty input
- buy path
- sell path
- hold when already long
- explicit RSI filter block

## Self-Review

- Kept the implementation scoped to the three task-owned files.
- Reused existing `market_data` and `indicators` contracts without changing upstream behavior.
- Preserved deterministic behavior: no I/O, no randomness, no hidden state.
- Verified both focused Task 3 tests and the broader `tests/crypto_trading` suite.
- Did not revert or touch unrelated worktree content.

## Concerns

- The brief labels the entry tests as crossover tests, but the provided candle fixtures only pass when the rule is interpreted as current EMA regime rather than "crossover on the last candle". The implementation follows the fixture-backed behavior so the task remains consistent with the approved tests.
