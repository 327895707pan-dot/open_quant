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


class PositionStore:
    def __init__(self, store: CryptoDuckDBStore):
        self.store = store

    async def handle_event(self, event: BaseEvent) -> None:
        if not isinstance(event, AccountUpdateEvent):
            return
        for raw_position in event.positions or (event.raw.get("a") or {}).get("P", []):
            position = {
                "symbol": raw_position.get("s"),
                "position_side": raw_position.get("ps", "BOTH"),
                "position_amt": _to_float(raw_position.get("pa")),
                "entry_price": _to_float(raw_position.get("ep")),
                "breakeven_price": _to_float(raw_position.get("bep")),
                "unrealized_pnl": _to_float(raw_position.get("up")),
                "margin_type": raw_position.get("mt"),
                "isolated_wallet": _to_float(raw_position.get("iw")),
                "event_time": event.event_time,
                "transaction_time": event.transaction_time,
            }
            if position["symbol"]:
                self.store.upsert_position(position)
                logger.debug("Updated position %s", position["symbol"])

    def get_positions(self) -> list[dict]:
        return self.store.get_positions()
