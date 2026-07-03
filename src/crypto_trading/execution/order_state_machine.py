from __future__ import annotations

import json
from typing import Any

from crypto_trading.events.models import OrderTradeUpdateEvent

TERMINAL_STATUSES = {"FILLED", "CANCELED", "EXPIRED", "EXPIRED_IN_MATCH"}


class OrderStateMachine:
    def __init__(self) -> None:
        self._orders: dict[tuple[str, int], dict[str, Any]] = {}
        self._seen_fills: set[tuple[str, int, int]] = set()

    def apply(self, event: OrderTradeUpdateEvent) -> dict[str, Any]:
        if event.symbol is None or event.order_id is None:
            return {"order": {}, "fill": None, "ignored": True, "reason": "missing order key"}
        key = (event.symbol, event.order_id)
        current = self._orders.get(key)
        incoming_time = event.transaction_time or event.order_trade_time or event.event_time or 0
        current_time = current.get("transaction_time", 0) if current else 0
        if current and incoming_time < current_time:
            return {"order": current, "fill": None, "ignored": True, "reason": "older event"}
        order = self._event_to_order(event)
        order["special_reason"] = self._special_reason(event.client_order_id)
        order["is_terminal"] = event.order_status in TERMINAL_STATUSES
        self._orders[key] = order
        fill = None
        if event.execution_type == "TRADE" and (event.last_filled_qty or 0) > 0 and event.trade_id is not None:
            fill_key = (event.symbol, event.order_id, event.trade_id)
            if fill_key not in self._seen_fills:
                self._seen_fills.add(fill_key)
                fill = {
                    "symbol": event.symbol,
                    "order_id": event.order_id,
                    "trade_id": event.trade_id,
                    "side": event.side,
                    "price": event.last_filled_price,
                    "qty": event.last_filled_qty,
                    "commission": event.commission,
                    "commission_asset": event.commission_asset,
                    "realized_profit": event.realized_profit,
                    "maker": event.maker,
                    "event_time": event.event_time,
                    "transaction_time": event.transaction_time,
                    "raw_json": json.dumps(event.raw, ensure_ascii=False),
                }
        return {"order": order, "fill": fill, "ignored": False, "reason": None}

    def _event_to_order(self, event: OrderTradeUpdateEvent) -> dict[str, Any]:
        return {
            "symbol": event.symbol,
            "order_id": event.order_id,
            "client_order_id": event.client_order_id,
            "side": event.side,
            "order_type": event.order_type,
            "time_in_force": event.time_in_force,
            "original_qty": event.original_qty,
            "original_price": event.original_price,
            "avg_price": event.avg_price,
            "stop_price": event.stop_price,
            "execution_type": event.execution_type,
            "order_status": event.order_status,
            "last_filled_qty": event.last_filled_qty,
            "accumulated_filled_qty": event.accumulated_filled_qty,
            "last_filled_price": event.last_filled_price,
            "commission_asset": event.commission_asset,
            "commission": event.commission,
            "trade_id": event.trade_id,
            "realized_profit": event.realized_profit,
            "reduce_only": event.reduce_only,
            "position_side": event.position_side,
            "event_time": event.event_time,
            "transaction_time": event.transaction_time or event.order_trade_time or event.event_time,
        }

    def _special_reason(self, client_order_id: str | None) -> str | None:
        if not client_order_id:
            return None
        if client_order_id.startswith("autoclose-"):
            return "liquidation"
        if client_order_id == "adl_autoclose":
            return "ADL"
        if client_order_id.startswith("settlement_autoclose-"):
            return "settlement"
        return None
