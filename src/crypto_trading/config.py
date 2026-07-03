from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _parse_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_float(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _parse_int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _parse_symbols(value: str | None) -> list[str]:
    if not value:
        return ["BTCUSDT", "ETHUSDT"]
    return [item.strip().upper() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    api_key: str
    api_secret: str
    testnet: bool
    rest_base_url: str
    ws_base_url: str
    db_path: str
    log_level: str
    dry_run: bool
    demo_strategy_enable_trading: bool
    allowed_symbols: list[str]
    max_notional_per_order: float
    max_total_notional: float
    max_open_orders: int


def load_settings() -> Settings:
    load_dotenv()

    dry_run = _parse_bool(os.getenv("CRYPTO_TRADING_DRY_RUN"), True)
    api_key = os.getenv("BINANCE_FUTURES_API_KEY", "")
    api_secret = os.getenv("BINANCE_FUTURES_API_SECRET", "")

    if not dry_run and (not api_key or not api_secret):
        raise ValueError(
            "CRYPTO_TRADING_DRY_RUN=false requires BINANCE_FUTURES_API_KEY "
            "and BINANCE_FUTURES_API_SECRET to be set."
        )

    return Settings(
        api_key=api_key,
        api_secret=api_secret,
        testnet=_parse_bool(os.getenv("BINANCE_FUTURES_TESTNET"), True),
        rest_base_url=os.getenv(
            "BINANCE_FUTURES_REST_BASE_URL", "https://testnet.binancefuture.com"
        ),
        ws_base_url=os.getenv("BINANCE_FUTURES_WS_BASE_URL", "wss://fstream.binance.com"),
        db_path=os.getenv("CRYPTO_TRADING_DB_PATH", "Data/crypto_trading.db"),
        log_level=os.getenv("CRYPTO_TRADING_LOG_LEVEL", "INFO").upper(),
        dry_run=dry_run,
        demo_strategy_enable_trading=_parse_bool(
            os.getenv("DEMO_STRATEGY_ENABLE_TRADING"), False
        ),
        allowed_symbols=_parse_symbols(os.getenv("CRYPTO_TRADING_ALLOWED_SYMBOLS")),
        max_notional_per_order=_parse_float(
            os.getenv("CRYPTO_TRADING_MAX_NOTIONAL_PER_ORDER"), 50.0
        ),
        max_total_notional=_parse_float(
            os.getenv("CRYPTO_TRADING_MAX_TOTAL_NOTIONAL"), 200.0
        ),
        max_open_orders=_parse_int(os.getenv("CRYPTO_TRADING_MAX_OPEN_ORDERS"), 5),
    )
