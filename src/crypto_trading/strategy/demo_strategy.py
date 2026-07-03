from __future__ import annotations

import logging

from crypto_trading.events.models import AccountUpdateEvent, OrderTradeUpdateEvent
from crypto_trading.strategy.base import BaseStrategy

logger = logging.getLogger(__name__)


class DemoStrategy(BaseStrategy):
    """Demo strategy for wiring only.

    demo_strategy is not investment advice and does not guarantee profit.
    It deliberately avoids grids, martingale logic, and unlimited averaging.
    """

    name = "demo_strategy"

    def __init__(self, symbols: list[str], enable_trading: bool = False):
        super().__init__(symbols)
        self.enable_trading = enable_trading

    async def on_order_update(self, event: OrderTradeUpdateEvent) -> None:
        logger.info("Order update %s %s status=%s exec=%s", event.symbol, event.order_id, event.order_status, event.execution_type)

    async def on_account_update(self, event: AccountUpdateEvent) -> None:
        logger.info("Account update reason=%s balances=%d positions=%d", event.reason, len(event.balances), len(event.positions))

    async def on_timer(self) -> None:
        if not self.enable_trading:
            return
        if not self.order_manager:
            logger.warning("Demo trading enabled but order manager is not configured")
            return
        logger.info("Demo trading enabled; no automatic order is sent without explicit code change")
