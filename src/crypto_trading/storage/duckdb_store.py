from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class CryptoDuckDBStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self.db_path)

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS raw_events (id VARCHAR, source VARCHAR, event_type VARCHAR, event_time BIGINT, transaction_time BIGINT, symbol VARCHAR, raw_json VARCHAR, received_at TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS orders (symbol VARCHAR, order_id BIGINT, client_order_id VARCHAR, side VARCHAR, order_type VARCHAR, time_in_force VARCHAR, original_qty DOUBLE, original_price DOUBLE, avg_price DOUBLE, stop_price DOUBLE, execution_type VARCHAR, order_status VARCHAR, last_filled_qty DOUBLE, accumulated_filled_qty DOUBLE, last_filled_price DOUBLE, commission_asset VARCHAR, commission DOUBLE, trade_id BIGINT, realized_profit DOUBLE, reduce_only BOOLEAN, position_side VARCHAR, event_time BIGINT, transaction_time BIGINT, updated_at TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS fills (symbol VARCHAR, order_id BIGINT, trade_id BIGINT, side VARCHAR, price DOUBLE, qty DOUBLE, commission DOUBLE, commission_asset VARCHAR, realized_profit DOUBLE, maker BOOLEAN, event_time BIGINT, transaction_time BIGINT, raw_json VARCHAR)")
            conn.execute("CREATE TABLE IF NOT EXISTS positions (symbol VARCHAR, position_side VARCHAR, position_amt DOUBLE, entry_price DOUBLE, breakeven_price DOUBLE, unrealized_pnl DOUBLE, margin_type VARCHAR, isolated_wallet DOUBLE, event_time BIGINT, transaction_time BIGINT, updated_at TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS balances (asset VARCHAR, wallet_balance DOUBLE, cross_wallet_balance DOUBLE, balance_change DOUBLE, event_time BIGINT, transaction_time BIGINT, updated_at TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS account_updates (id VARCHAR, event_time BIGINT, transaction_time BIGINT, reason VARCHAR, raw_json VARCHAR, received_at TIMESTAMP)")
            conn.execute("CREATE TABLE IF NOT EXISTS stream_status (id VARCHAR, status VARCHAR, message VARCHAR, listen_key VARCHAR, event_time BIGINT, created_at TIMESTAMP)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_key ON orders(symbol, order_id)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_fills_key ON fills(symbol, order_id, trade_id)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_positions_key ON positions(symbol, position_side)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_balances_key ON balances(asset)")

    def insert_raw_event(self, event: dict[str, Any], source: str) -> str:
        event_id = str(uuid.uuid4())
        order = event.get("o") or {}
        symbol = event.get("s") or order.get("s")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO raw_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [event_id, source, event.get("e"), event.get("E"), event.get("T"), symbol, _json(event), _now()],
            )
        return event_id

    def upsert_order(self, order: dict[str, Any]) -> None:
        columns = ["symbol", "order_id", "client_order_id", "side", "order_type", "time_in_force", "original_qty", "original_price", "avg_price", "stop_price", "execution_type", "order_status", "last_filled_qty", "accumulated_filled_qty", "last_filled_price", "commission_asset", "commission", "trade_id", "realized_profit", "reduce_only", "position_side", "event_time", "transaction_time", "updated_at"]
        payload = {**order, "updated_at": _now()}
        with self._connect() as conn:
            conn.execute("DELETE FROM orders WHERE symbol = ? AND order_id = ?", [payload.get("symbol"), payload.get("order_id")])
            conn.execute(f"INSERT INTO orders ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", [payload.get(column) for column in columns])

    def insert_fill(self, fill: dict[str, Any]) -> bool:
        columns = ["symbol", "order_id", "trade_id", "side", "price", "qty", "commission", "commission_asset", "realized_profit", "maker", "event_time", "transaction_time", "raw_json"]
        payload = {**fill}
        if not isinstance(payload.get("raw_json"), str):
            payload["raw_json"] = _json(payload.get("raw_json") or {})
        with self._connect() as conn:
            exists = conn.execute("SELECT COUNT(*) FROM fills WHERE symbol = ? AND order_id = ? AND trade_id = ?", [payload.get("symbol"), payload.get("order_id"), payload.get("trade_id")]).fetchone()[0]
            if exists:
                return False
            conn.execute(f"INSERT INTO fills ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", [payload.get(column) for column in columns])
        return True

    def upsert_position(self, position: dict[str, Any]) -> None:
        columns = ["symbol", "position_side", "position_amt", "entry_price", "breakeven_price", "unrealized_pnl", "margin_type", "isolated_wallet", "event_time", "transaction_time", "updated_at"]
        payload = {**position, "updated_at": _now()}
        with self._connect() as conn:
            conn.execute("DELETE FROM positions WHERE symbol = ? AND position_side = ?", [payload.get("symbol"), payload.get("position_side")])
            conn.execute(f"INSERT INTO positions ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", [payload.get(column) for column in columns])

    def upsert_balance(self, balance: dict[str, Any]) -> None:
        columns = ["asset", "wallet_balance", "cross_wallet_balance", "balance_change", "event_time", "transaction_time", "updated_at"]
        payload = {**balance, "updated_at": _now()}
        with self._connect() as conn:
            conn.execute("DELETE FROM balances WHERE asset = ?", [payload.get("asset")])
            conn.execute(f"INSERT INTO balances ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", [payload.get(column) for column in columns])

    def insert_account_update(self, update: dict[str, Any]) -> str:
        update_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute("INSERT INTO account_updates VALUES (?, ?, ?, ?, ?, ?)", [update_id, update.get("event_time"), update.get("transaction_time"), update.get("reason"), _json(update.get("raw") or update), _now()])
        return update_id

    def insert_stream_status(self, status: dict[str, Any]) -> str:
        status_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute("INSERT INTO stream_status VALUES (?, ?, ?, ?, ?, ?)", [status_id, status.get("status"), status.get("message"), status.get("listen_key"), status.get("event_time"), _now()])
        return status_id

    def get_order(self, symbol: str, order_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM orders WHERE symbol = ? AND order_id = ?", [symbol, order_id]).fetch_df()
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        terminal = ("FILLED", "CANCELED", "EXPIRED", "EXPIRED_IN_MATCH")
        placeholders = ", ".join("?" for _ in terminal)
        params: list[Any] = list(terminal)
        sql = f"SELECT * FROM orders WHERE order_status NOT IN ({placeholders})"
        if symbol:
            sql += " AND symbol = ?"
            params.append(symbol)
        with self._connect() as conn:
            return conn.execute(sql, params).fetch_df().to_dict("records")

    def get_positions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM positions").fetch_df().to_dict("records")

    def get_balances(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM balances").fetch_df().to_dict("records")
