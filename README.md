# Binance Futures Event System

`binance-futures-event-system` is a Python skeleton for a Binance USD-M Futures
event-driven trading system.

It is designed around Binance User Data Stream events. Raw WebSocket messages are
persisted first, parsed into internal events, published through an event bus, and
then applied to order, fill, account, and position state.

## Core Features

- Binance User Data Stream integration
- Raw event persistence in DuckDB
- `ORDER_TRADE_UPDATE` parsing
- `ACCOUNT_UPDATE` parsing
- Order state machine
- Account and position state stores
- Local DuckDB storage
- Risk controls
- `dry_run` execution mode
- Testnet-first configuration
- `demo_strategy` for wiring verification only
- REST reconciliation

## Architecture

```text
Binance WebSocket
    -> raw_events
    -> EventParser
    -> EventBus
    -> OrderStore / PositionStore / AccountStore
    -> Strategy
    -> RiskManager
    -> OrderManager
    -> Binance REST
```

## Install

```bash
pip install -e .
```

## Configure

```bash
cp .env.example .env
```

Defaults are intentionally conservative:

- `BINANCE_FUTURES_TESTNET=true`
- `CRYPTO_TRADING_DRY_RUN=true`
- `DEMO_STRATEGY_ENABLE_TRADING=false`

Never commit `.env` or real API credentials.

## Run

```bash
python -m crypto_trading.main
```

Starting the live user stream requires Binance API credentials. Parser, storage,
state-machine, and risk tests do not require network access or real keys.

## Test

```bash
pytest tests/crypto_trading -q
```

## Safety Principles

- Testnet by default.
- Dry run by default.
- Do not submit or commit API keys.
- WebSocket unhealthy state blocks new positions.
- A REST order response is not treated as a fill.
- Order state changes must arrive through `ORDER_TRADE_UPDATE`.
- Raw WebSocket events are saved before parsing or state mutation.

## Risk Notice

Futures trading is extremely risky. This project is not investment advice and
does not guarantee profit. The included `demo_strategy` is only for validating
system wiring.
