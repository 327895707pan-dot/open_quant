from __future__ import annotations

import logging
from typing import Any

from crypto_trading.events.models import AccountUpdateEvent, BaseEvent
from crypto_trading.storage.duckdb_store import CryptoDuckDBStore

logger = logging.getLogger(__name__)


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class AccountStore:
    def __init__(self, store: CryptoDuckDBStore):
        self.store = store

    async def handle_event(self, event: BaseEvent) -> None:
        if not isinstance(event, AccountUpdateEvent):
            return
        self.store.insert_account_update({"event_time": event.event_time, "transaction_time": event.transaction_time, "reason": event.reason, "raw": event.raw})
        for raw_balance in event.balances or (event.raw.get("a") or {}).get("B", []):
            balance = {
                "asset": raw_balance.get("a"),
                "wallet_balance": _to_float(raw_balance.get("wb")),
                "cross_wallet_balance": _to_float(raw_balance.get("cw")),
                "balance_change": _to_float(raw_balance.get("bc")),
                "event_time": event.event_time,
                "transaction_time": event.transaction_time,
            }
            if balance["asset"]:
                self.store.upsert_balance(balance)
                logger.debug("Updated balance %s", balance["asset"])

    def get_balances(self) -> list[dict]:
        return self.store.get_balances()
