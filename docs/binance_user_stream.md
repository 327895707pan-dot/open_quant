# Binance User Data Stream

The user stream lifecycle is:

1. Create a `listenKey` through `POST /fapi/v1/listenKey`.
2. Connect to `wss://fstream.binance.com/private/ws/<listenKey>`.
3. Persist every raw message to DuckDB.
4. Parse and publish the event.
5. Keep the listen key alive with `PUT /fapi/v1/listenKey`.
6. Reconnect before the WebSocket reaches its 24-hour connection window.

Handled event types:

- `ORDER_TRADE_UPDATE`
- `ACCOUNT_UPDATE`
- `MARGIN_CALL`
- `ACCOUNT_CONFIG_UPDATE`
- `TRADE_LITE`
- `CONDITIONAL_ORDER_TRIGGER_REJECT`
- `listenKeyExpired`

When `listenKeyExpired` is received, the stream is marked unhealthy, the current
connection is closed, a new listen key is created, and REST reconciliation should
run after reconnection.
