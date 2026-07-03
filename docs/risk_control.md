# Risk Control

Risk checks run before every order request.

Current checks:

- Reject symbols outside `CRYPTO_TRADING_ALLOWED_SYMBOLS`.
- Reject new positions when the WebSocket stream is unhealthy.
- Enforce `CRYPTO_TRADING_MAX_NOTIONAL_PER_ORDER`.
- Enforce `CRYPTO_TRADING_MAX_TOTAL_NOTIONAL`.
- Enforce `CRYPTO_TRADING_MAX_OPEN_ORDERS`.
- If new positions are disabled, allow only reduce-only orders.
- In `dry_run`, return a simulated request instead of calling REST.

`dry_run` is not a bypass for validation. It only prevents real REST order
submission after validation succeeds.

Before moving to production, reduce limits, verify exchange permissions, confirm
position mode, and run the system on testnet for enough time to observe
disconnects, keepalive, fills, cancels, and reconciliation.
