from __future__ import annotations

import logging
import time
from typing import Any

from crypto_trading.exchange.binance_futures_rest import BinanceFuturesRESTClient
from crypto_trading.risk.risk_manager import RiskManager
from crypto_trading.storage.duckdb_store import CryptoDuckDBStore

logger = logging.getLogger(__name__)


class OrderManager:
    def __init__(self, rest_client: BinanceFuturesRESTClient, risk_manager: RiskManager, store: CryptoDuckDBStore, *, dry_run: bool = True, strategy_name: str = "demo") -> None:
        self.rest_client = rest_client
        self.risk_manager = risk_manager
        self.store = store
        self.dry_run = dry_run
        self.strategy_name = strategy_name

    async def create_market_order(self, *, symbol: str, side: str, quantity: float, reduce_only: bool = False, position_side: str | None = None) -> dict[str, Any]:
        check = self.risk_manager.check_order(symbol=symbol, side=side, quantity=quantity, order_type="MARKET", reduce_only=reduce_only)
        if not check.allowed:
            raise ValueError(f"Risk check rejected order: {check.reason}")
        request = {"symbol": symbol, "side": side, "type": "MARKET", "quantity": quantity, "reduceOnly": reduce_only, "positionSide": position_side, "newClientOrderId": self._client_order_id(symbol)}
        if self.dry_run:
            logger.info("dry_run market order request: %s", request)
            return {"dry_run": True, "request": request}
        return await self.rest_client.create_order(**request)

    async def create_limit_order(self, *, symbol: str, side: str, quantity: float, price: float, time_in_force: str = "GTC", reduce_only: bool = False, position_side: str | None = None) -> dict[str, Any]:
        check = self.risk_manager.check_order(symbol=symbol, side=side, quantity=quantity, price=price, order_type="LIMIT", reduce_only=reduce_only)
        if not check.allowed:
            raise ValueError(f"Risk check rejected order: {check.reason}")
        request = {"symbol": symbol, "side": side, "type": "LIMIT", "quantity": quantity, "price": price, "timeInForce": time_in_force, "reduceOnly": reduce_only, "positionSide": position_side, "newClientOrderId": self._client_order_id(symbol)}
        if self.dry_run:
            logger.info("dry_run limit order request: %s", request)
            return {"dry_run": True, "request": request}
        return await self.rest_client.create_order(**request)

    async def cancel_order(self, symbol: str, order_id: int | None = None, client_order_id: str | None = None) -> dict[str, Any]:
        if self.dry_run:
            request = {"symbol": symbol, "order_id": order_id, "client_order_id": client_order_id}
            logger.info("dry_run cancel order request: %s", request)
            return {"dry_run": True, "request": request}
        return await self.rest_client.cancel_order(symbol, order_id, client_order_id)

    async def close_position_market(self, *, symbol: str, side: str, quantity: float, position_side: str | None = None) -> dict[str, Any]:
        return await self.create_market_order(symbol=symbol, side=side, quantity=quantity, reduce_only=True, position_side=position_side)

    def _client_order_id(self, symbol: str) -> str:
        return f"oq_{self.strategy_name}_{symbol}_{int(time.time() * 1000)}"
