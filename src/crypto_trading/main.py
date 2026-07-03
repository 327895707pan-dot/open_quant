from __future__ import annotations

import asyncio
import logging

from crypto_trading.config import load_settings
from crypto_trading.events.event_bus import EventBus
from crypto_trading.events.models import ListenKeyExpiredEvent, UnknownEvent
from crypto_trading.events.parser import EventParser
from crypto_trading.exchange.binance_futures_rest import BinanceFuturesRESTClient
from crypto_trading.exchange.binance_futures_ws import BinanceFuturesUserDataStream
from crypto_trading.execution.order_manager import OrderManager
from crypto_trading.execution.order_state_machine import OrderStateMachine
from crypto_trading.logging_config import setup_logging
from crypto_trading.reconcile.reconciler import Reconciler
from crypto_trading.risk.risk_manager import RiskManager
from crypto_trading.state.account_store import AccountStore
from crypto_trading.state.order_store import OrderStore
from crypto_trading.state.position_store import PositionStore
from crypto_trading.storage.duckdb_store import CryptoDuckDBStore
from crypto_trading.strategy.demo_strategy import DemoStrategy

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    if not settings.api_key or not settings.api_secret:
        raise RuntimeError("BINANCE_FUTURES_API_KEY and BINANCE_FUTURES_API_SECRET are required to start the live user data stream. Parser/storage tests do not need real credentials.")
    store = CryptoDuckDBStore(settings.db_path)
    store.init_schema()
    rest_client = BinanceFuturesRESTClient(settings.api_key, settings.api_secret, settings.rest_base_url)
    parser = EventParser()
    event_bus = EventBus()
    state_machine = OrderStateMachine()
    order_store = OrderStore(store, state_machine)
    position_store = PositionStore(store)
    account_store = AccountStore(store)
    risk_manager = RiskManager(max_notional_per_order=settings.max_notional_per_order, max_total_notional=settings.max_total_notional, allowed_symbols=settings.allowed_symbols, max_open_orders=settings.max_open_orders, dry_run=settings.dry_run, store=store, system_health=event_bus.system_health)
    order_manager = OrderManager(rest_client, risk_manager, store, dry_run=settings.dry_run, strategy_name=DemoStrategy.name)
    strategy = DemoStrategy(settings.allowed_symbols, settings.demo_strategy_enable_trading)
    strategy.set_order_manager(order_manager)
    reconciler = Reconciler(rest_client, store)
    stream = BinanceFuturesUserDataStream(rest_client, store, parser, event_bus, settings.ws_base_url, dry_run=settings.dry_run)
    event_bus.register("ORDER_TRADE_UPDATE", order_store.handle_event)
    event_bus.register("ORDER_TRADE_UPDATE", strategy.on_order_update)
    event_bus.register("ACCOUNT_UPDATE", account_store.handle_event)
    event_bus.register("ACCOUNT_UPDATE", position_store.handle_event)
    event_bus.register("ACCOUNT_UPDATE", strategy.on_account_update)
    event_bus.register("listenKeyExpired", _handle_listen_key_expired(event_bus))
    event_bus.register("UNKNOWN", _handle_unknown)
    await event_bus.start()
    try:
        await reconciler.full_reconcile()
        await stream.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        await stream.stop()
        await event_bus.stop()
        await rest_client.close()
        store.insert_stream_status({"status": "stopped", "message": "application stopped"})


def _handle_listen_key_expired(event_bus: EventBus):
    async def handler(event: ListenKeyExpiredEvent) -> None:
        event_bus.system_health["stream_healthy"] = False
        logger.warning("listenKeyExpired received at %s", event.event_time)
    return handler


async def _handle_unknown(event: UnknownEvent) -> None:
    logger.info("Unknown event ignored: %s", event.event_type)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
