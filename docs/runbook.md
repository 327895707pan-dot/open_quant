# Runbook

## Setup

```bash
pip install -e .
cp .env.example .env
```

Fill `.env` with testnet credentials. Keep:

```text
BINANCE_FUTURES_TESTNET=true
CRYPTO_TRADING_DRY_RUN=true
DEMO_STRATEGY_ENABLE_TRADING=false
```

## Run

```bash
python -m crypto_trading.main
```

## Test

```bash
pytest tests/crypto_trading -q
python -m compileall src/crypto_trading
```

## Operational Checks

- Confirm API key has only the permissions required.
- Confirm `.env` is ignored by Git.
- Confirm no key or secret is hard-coded in source.
- Confirm `raw_events` is receiving messages.
- Confirm `ORDER_TRADE_UPDATE` updates orders and fills.
- Confirm `ACCOUNT_UPDATE` updates balances and positions.
- Confirm stream unhealthy state blocks new positions.
- Confirm REST reconciliation works after startup and reconnects.

## Moving From Testnet To Production

Production requires changing base URLs and credentials deliberately. Keep
`dry_run=true` for the first production connectivity check, then reduce limits
before any live order is allowed. Do not enable `demo_strategy` trading unless
you have reviewed and accepted the order path and risk controls.
