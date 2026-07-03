from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BaseEvent:
    event_type: str
    event_time: int | None
    transaction_time: int | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class OrderTradeUpdateEvent(BaseEvent):
    symbol: str | None = None
    client_order_id: str | None = None
    side: str | None = None
    order_type: str | None = None
    time_in_force: str | None = None
    original_qty: float | None = None
    original_price: float | None = None
    avg_price: float | None = None
    stop_price: float | None = None
    execution_type: str | None = None
    order_status: str | None = None
    order_id: int | None = None
    last_filled_qty: float | None = None
    accumulated_filled_qty: float | None = None
    last_filled_price: float | None = None
    commission_asset: str | None = None
    commission: float | None = None
    order_trade_time: int | None = None
    trade_id: int | None = None
    maker: bool | None = None
    reduce_only: bool | None = None
    working_type: str | None = None
    original_order_type: str | None = None
    position_side: str | None = None
    close_all: bool | None = None
    realized_profit: float | None = None
    expiry_reason: int | None = None


@dataclass(frozen=True)
class AccountUpdateEvent(BaseEvent):
    reason: str | None = None
    balances: list[dict[str, Any]] = field(default_factory=list)
    positions: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class MarginCallEvent(BaseEvent):
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AccountConfigUpdateEvent(BaseEvent):
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TradeLiteEvent(BaseEvent):
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConditionalOrderTriggerRejectEvent(BaseEvent):
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ListenKeyExpiredEvent(BaseEvent):
    listen_key: str | None = None


@dataclass(frozen=True)
class UnknownEvent(BaseEvent):
    reason: str | None = None
