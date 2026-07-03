from __future__ import annotations

import logging

from crypto_trading.events.models import BaseEvent, OrderTradeUpdateEvent
from crypto_trading.execution.order_state_machine import OrderStateMachine
from crypto_trading.storage.duckdb_store import CryptoDuckDBStore

logger = logging.getLogger(__name__)


class OrderStore:
    def __init__(self, store: CryptoDuckDBStore, state_machine: OrderStateMachine):
        self.store = store
        self.state_machine = state_machine

    async def handle_event(self, event: BaseEvent) -> None:
        if not isinstance(event, OrderTradeUpdateEvent):
            return
        result = self.state_machine.apply(event)
        if result["ignored"]:
            logger.info("Ignored order event: %s", result["reason"])
            return
        self.store.upsert_order(result["order"])
        if result["fill"]:
            self.store.insert_fill(result["fill"])

    def get_open_orders(self, symbol: str | None = None) -> list[dict]:
        return self.store.get_open_orders(symbol)

    def get_order(self, symbol: str, order_id: int) -> dict | None:
        return self.store.get_order(symbol, order_id)
