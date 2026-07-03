from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from crypto_trading.storage.duckdb_store import CryptoDuckDBStore


@dataclass(frozen=True)
class RiskCheckResult:
    allowed: bool
    reason: str | None = None
    dry_run: bool = True


class RiskManager:
    def __init__(self, *, max_notional_per_order: float, max_total_notional: float, allowed_symbols: list[str], max_open_orders: int, max_leverage: float = 1.0, allow_new_position: bool = True, reduce_only_when_unhealthy: bool = True, daily_loss_limit: float | None = None, dry_run: bool = True, store: CryptoDuckDBStore | None = None, system_health: dict[str, Any] | None = None) -> None:
        self.max_notional_per_order = max_notional_per_order
        self.max_total_notional = max_total_notional
        self.max_leverage = max_leverage
        self.allowed_symbols = {symbol.upper() for symbol in allowed_symbols}
        self.allow_new_position = allow_new_position
        self.reduce_only_when_unhealthy = reduce_only_when_unhealthy
        self.max_open_orders = max_open_orders
        self.daily_loss_limit = daily_loss_limit
        self.dry_run = dry_run
        self.store = store
        self.system_health = system_health or {"stream_healthy": True}

    def check_order(self, *, symbol: str, side: str, quantity: float, price: float | None = None, order_type: str = "MARKET", reduce_only: bool = False) -> RiskCheckResult:
        del side, order_type
        symbol = symbol.upper()
        if symbol not in self.allowed_symbols:
            return self._reject(f"{symbol} is not in allowed_symbols")
        stream_healthy = bool(self.system_health.get("stream_healthy", True))
        if not stream_healthy and not reduce_only:
            return self._reject("websocket stream is unhealthy; new positions are blocked")
        if not stream_healthy and reduce_only and not self.reduce_only_when_unhealthy:
            return self._reject("websocket stream is unhealthy")
        if not self.allow_new_position and not reduce_only:
            return self._reject("new positions are disabled")
        notional = abs(quantity * (price if price is not None else 1.0))
        if notional > self.max_notional_per_order:
            return self._reject("order notional exceeds max_notional_per_order")
        open_orders = self.store.get_open_orders() if self.store else []
        if len(open_orders) >= self.max_open_orders:
            return self._reject("open orders exceed max_open_orders")
        total_notional = self._current_total_notional()
        if not reduce_only and total_notional + notional > self.max_total_notional:
            return self._reject("total notional exceeds max_total_notional")
        return RiskCheckResult(True, dry_run=self.dry_run)

    def _current_total_notional(self) -> float:
        if not self.store:
            return 0.0
        return sum(abs(float(p.get("position_amt") or 0.0) * float(p.get("entry_price") or 0.0)) for p in self.store.get_positions())

    def _reject(self, reason: str) -> RiskCheckResult:
        return RiskCheckResult(False, reason=reason, dry_run=self.dry_run)
