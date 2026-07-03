from __future__ import annotations

from typing import Any

from crypto_trading.events.models import (
    AccountConfigUpdateEvent,
    AccountUpdateEvent,
    BaseEvent,
    ConditionalOrderTriggerRejectEvent,
    ListenKeyExpiredEvent,
    MarginCallEvent,
    OrderTradeUpdateEvent,
    TradeLiteEvent,
    UnknownEvent,
)


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


class EventParser:
    def parse(self, raw: dict[str, Any]) -> BaseEvent:
        event_type = raw.get("e")
        if event_type == "ORDER_TRADE_UPDATE":
            return self.parse_order_trade_update(raw)
        if event_type == "ACCOUNT_UPDATE":
            return self.parse_account_update(raw)
        if event_type == "listenKeyExpired":
            return self.parse_listen_key_expired(raw)
        if event_type == "TRADE_LITE":
            return self.parse_trade_lite(raw)
        if event_type == "MARGIN_CALL":
            return self.parse_margin_call(raw)
        if event_type == "ACCOUNT_CONFIG_UPDATE":
            return self.parse_account_config_update(raw)
        if event_type == "CONDITIONAL_ORDER_TRIGGER_REJECT":
            return self.parse_conditional_order_trigger_reject(raw)
        return UnknownEvent(
            event_type=event_type or "UNKNOWN",
            event_time=_safe_int(raw.get("E")),
            transaction_time=_safe_int(raw.get("T")),
            raw=raw,
            reason="unsupported event type",
        )

    def parse_order_trade_update(self, raw: dict[str, Any]) -> OrderTradeUpdateEvent:
        order = raw.get("o") or {}
        return OrderTradeUpdateEvent(
            event_type="ORDER_TRADE_UPDATE",
            event_time=_safe_int(raw.get("E")),
            transaction_time=_safe_int(raw.get("T")),
            raw=raw,
            symbol=order.get("s"),
            client_order_id=order.get("c"),
            side=order.get("S"),
            order_type=order.get("o"),
            time_in_force=order.get("f"),
            original_qty=_safe_float(order.get("q")),
            original_price=_safe_float(order.get("p")),
            avg_price=_safe_float(order.get("ap")),
            stop_price=_safe_float(order.get("sp")),
            execution_type=order.get("x"),
            order_status=order.get("X"),
            order_id=_safe_int(order.get("i")),
            last_filled_qty=_safe_float(order.get("l")),
            accumulated_filled_qty=_safe_float(order.get("z")),
            last_filled_price=_safe_float(order.get("L")),
            commission_asset=order.get("N"),
            commission=_safe_float(order.get("n")),
            order_trade_time=_safe_int(order.get("T")),
            trade_id=_safe_int(order.get("t")),
            maker=_safe_bool(order.get("m")),
            reduce_only=_safe_bool(order.get("R")),
            working_type=order.get("wt"),
            original_order_type=order.get("ot"),
            position_side=order.get("ps"),
            close_all=_safe_bool(order.get("cp")),
            realized_profit=_safe_float(order.get("rp")),
            expiry_reason=_safe_int(order.get("er")),
        )

    def parse_account_update(self, raw: dict[str, Any]) -> AccountUpdateEvent:
        account = raw.get("a") or {}
        return AccountUpdateEvent(
            event_type="ACCOUNT_UPDATE",
            event_time=_safe_int(raw.get("E")),
            transaction_time=_safe_int(raw.get("T")),
            raw=raw,
            reason=account.get("m"),
            balances=list(account.get("B") or []),
            positions=list(account.get("P") or []),
        )

    def parse_listen_key_expired(self, raw: dict[str, Any]) -> ListenKeyExpiredEvent:
        return ListenKeyExpiredEvent(
            event_type="listenKeyExpired",
            event_time=_safe_int(raw.get("E")),
            transaction_time=_safe_int(raw.get("T")),
            raw=raw,
            listen_key=raw.get("listenKey"),
        )

    def parse_trade_lite(self, raw: dict[str, Any]) -> TradeLiteEvent:
        return TradeLiteEvent("TRADE_LITE", _safe_int(raw.get("E")), _safe_int(raw.get("T")), raw, raw)

    def parse_margin_call(self, raw: dict[str, Any]) -> MarginCallEvent:
        return MarginCallEvent("MARGIN_CALL", _safe_int(raw.get("E")), _safe_int(raw.get("T")), raw, raw)

    def parse_account_config_update(self, raw: dict[str, Any]) -> AccountConfigUpdateEvent:
        return AccountConfigUpdateEvent(
            "ACCOUNT_CONFIG_UPDATE", _safe_int(raw.get("E")), _safe_int(raw.get("T")), raw, raw
        )

    def parse_conditional_order_trigger_reject(
        self, raw: dict[str, Any]
    ) -> ConditionalOrderTriggerRejectEvent:
        return ConditionalOrderTriggerRejectEvent(
            "CONDITIONAL_ORDER_TRIGGER_REJECT",
            _safe_int(raw.get("E")),
            _safe_int(raw.get("T")),
            raw,
            raw,
        )
