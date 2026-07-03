from crypto_trading.storage.duckdb_store import CryptoDuckDBStore


def test_raw_events_orders_fills_and_state_are_persisted(tmp_path):
    store = CryptoDuckDBStore(str(tmp_path / "crypto.db"))
    store.init_schema()
    store.insert_raw_event({"e": "ORDER_TRADE_UPDATE", "E": 1, "T": 2, "o": {"s": "BTCUSDT"}}, "test")
    order = {"symbol": "BTCUSDT", "order_id": 1, "client_order_id": "c1", "side": "BUY", "order_type": "LIMIT", "time_in_force": "GTC", "original_qty": 0.1, "original_price": 100.0, "avg_price": 0.0, "stop_price": 0.0, "execution_type": "NEW", "order_status": "NEW", "last_filled_qty": 0.0, "accumulated_filled_qty": 0.0, "last_filled_price": 0.0, "commission_asset": None, "commission": 0.0, "trade_id": 0, "realized_profit": 0.0, "reduce_only": False, "position_side": "BOTH", "event_time": 1, "transaction_time": 1}
    store.upsert_order(order)
    order["order_status"] = "PARTIALLY_FILLED"
    store.upsert_order(order)
    assert store.get_order("BTCUSDT", 1)["order_status"] == "PARTIALLY_FILLED"
    assert len(store.get_open_orders("BTCUSDT")) == 1
    fill = {"symbol": "BTCUSDT", "order_id": 1, "trade_id": 9, "side": "BUY", "price": 100.0, "qty": 0.1, "commission": 0.01, "commission_asset": "USDT", "realized_profit": 0.0, "maker": False, "event_time": 2, "transaction_time": 2, "raw_json": {"e": "ORDER_TRADE_UPDATE"}}
    assert store.insert_fill(fill) is True
    assert store.insert_fill(fill) is False
    store.upsert_position({"symbol": "BTCUSDT", "position_side": "BOTH", "position_amt": 0.1, "entry_price": 100.0, "breakeven_price": 100.0, "unrealized_pnl": 1.0, "margin_type": "cross", "isolated_wallet": 0.0, "event_time": 1, "transaction_time": 1})
    store.upsert_balance({"asset": "USDT", "wallet_balance": 100.0, "cross_wallet_balance": 100.0, "balance_change": 0.0, "event_time": 1, "transaction_time": 1})
    assert store.get_positions()[0]["symbol"] == "BTCUSDT"
    assert store.get_balances()[0]["asset"] == "USDT"
