from __future__ import annotations

from crypto_trading.events.models import AccountUpdateEvent, BaseEvent, OrderTradeUpdateEvent
from crypto_trading.execution.order_manager import OrderManager


class BaseStrategy:
    name = "base"

    def __init__(self, symbols: list[str]):
        self.symbols = symbols
        self.order_manager: OrderManager | None = None

    def set_order_manager(self, order_manager: OrderManager) -> None:
        self.order_manager = order_manager

    async def on_event(self, event: BaseEvent) -> None:
        del event

    async def on_order_update(self, event: OrderTradeUpdateEvent) -> None:
        del event

    async def on_account_update(self, event: AccountUpdateEvent) -> None:
        del event

    async def on_timer(self) -> None:
        return None
