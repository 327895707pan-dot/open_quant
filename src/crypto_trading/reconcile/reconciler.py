from __future__ import annotations

import logging
from typing import Any

from crypto_trading.exchange.binance_futures_rest import BinanceFuturesRESTClient
from crypto_trading.storage.duckdb_store import CryptoDuckDBStore

logger = logging.getLogger(__name__)


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class Reconciler:
    def __init__(self, rest_client: BinanceFuturesRESTClient, store: CryptoDuckDBStore, interval_seconds: int = 300) -> None:
        self.rest_client = rest_client
        self.store = store
        self.interval_seconds = interval_seconds

    async def reconcile_open_orders(self) -> None:
        for raw in await self.rest_client.get_open_orders():
            self.store.upsert_order({
                "symbol": raw.get("symbol"),
                "order_id": int(raw["orderId"]),
                "client_order_id": raw.get("clientOrderId"),
                "side": raw.get("side"),
                "order_type": raw.get("type"),
                "time_in_force": raw.get("timeInForce"),
                "original_qty": _to_float(raw.get("origQty")),
                "original_price": _to_float(raw.get("price")),
                "avg_price": _to_float(raw.get("avgPrice")),
                "stop_price": _to_float(raw.get("stopPrice")),
                "execution_type": "REST_SNAPSHOT",
                "order_status": raw.get("status"),
                "last_filled_qty": None,
                "accumulated_filled_qty": _to_float(raw.get("executedQty")),
                "last_filled_price": None,
                "commission_asset": None,
                "commission": None,
                "trade_id": None,
                "realized_profit": None,
                "reduce_only": raw.get("reduceOnly"),
                "position_side": raw.get("positionSide"),
                "event_time": raw.get("updateTime"),
                "transaction_time": raw.get("updateTime"),
            })
        self.store.insert_stream_status({"status": "reconciled", "message": "open orders reconciled"})

    async def reconcile_positions(self) -> None:
        for raw in await self.rest_client.get_position_risk():
            position = {
                "symbol": raw.get("symbol"),
                "position_side": raw.get("positionSide", "BOTH"),
                "position_amt": _to_float(raw.get("positionAmt")),
                "entry_price": _to_float(raw.get("entryPrice")),
                "breakeven_price": _to_float(raw.get("breakEvenPrice")),
                "unrealized_pnl": _to_float(raw.get("unRealizedProfit")),
                "margin_type": raw.get("marginType"),
                "isolated_wallet": _to_float(raw.get("isolatedWallet")),
                "event_time": raw.get("updateTime"),
                "transaction_time": raw.get("updateTime"),
            }
            if position["symbol"]:
                self.store.upsert_position(position)
        self.store.insert_stream_status({"status": "reconciled", "message": "positions reconciled"})

    async def reconcile_account(self) -> None:
        raw = await self.rest_client.get_account_info()
        for item in raw.get("assets", []):
            self.store.upsert_balance({"asset": item.get("asset"), "wallet_balance": _to_float(item.get("walletBalance")), "cross_wallet_balance": _to_float(item.get("crossWalletBalance")), "balance_change": None, "event_time": raw.get("updateTime"), "transaction_time": raw.get("updateTime")})
        self.store.insert_stream_status({"status": "reconciled", "message": "account reconciled"})

    async def full_reconcile(self) -> None:
        logger.info("Starting full REST reconciliation")
        await self.reconcile_open_orders()
        await self.reconcile_positions()
        await self.reconcile_account()
