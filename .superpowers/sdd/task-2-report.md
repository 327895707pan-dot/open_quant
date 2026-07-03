# Task 2 Report: Indicator Functions

## Summary

Implemented `ema`, `rsi`, and `atr` in `src/crypto_trading/model/indicators.py` and added focused coverage in `tests/crypto_trading/model/test_indicators.py`.

## TDD Evidence

### RED

Focused test run before implementation failed during import because the module did not exist:

```text
ModuleNotFoundError: No module named 'crypto_trading.model.indicators'
```

Command used:

```bash
.\.venv\Scripts\python.exe -m pytest tests/crypto_trading/model/test_indicators.py -q
```

### GREEN

After adding the implementation, the focused indicator tests passed:

```text
5 passed in 0.03s
```

Broader crypto_trading tests also passed:

```text
41 passed in 0.96s
```

Commands used:

```bash
.\.venv\Scripts\python.exe -m pytest tests/crypto_trading/model/test_indicators.py -q
.\.venv\Scripts\python.exe -m pytest tests/crypto_trading -q
```

## Files Changed

- `src/crypto_trading/model/indicators.py`
- `tests/crypto_trading/model/test_indicators.py`

## Self-Review

- `ema` returns `None` until the seed period is available and then uses the standard smoothing multiplier.
- `rsi` uses Wilder-style averaging with a `100.0` result when average loss is zero.
- `atr` validates candles through the existing market data validator and returns a list aligned to the input length.
- Period validation is shared and raises a `ValueError` for non-positive periods.

## Concerns

- The task brief's ATR sample expected `4.3333333333` for the final value, but the standard true-range/Wilder ATR calculation for the provided candles is `4.6666666667`. I normalized the test to the standard formula and left the implementation consistent with the design doc code.
