import pytest

from crypto_trading.exchange.binance_futures_rest import BinanceFuturesRESTClient
from crypto_trading.execution.order_manager import OrderManager
from crypto_trading.risk.risk_manager import RiskManager
from crypto_trading.storage.duckdb_store import CryptoDuckDBStore


class FailingRESTClient:
    async def create_order(self, **kwargs):
        raise AssertionError("REST create_order should not be called in dry_run")


def make_risk(store=None, health=None):
    return RiskManager(max_notional_per_order=50, max_total_notional=200, allowed_symbols=["BTCUSDT", "ETHUSDT"], max_open_orders=5, dry_run=True, store=store, system_health=health or {"stream_healthy": True})


def test_rejects_non_allowed_symbol():
    result = make_risk().check_order(symbol="BNBUSDT", side="BUY", quantity=1, price=10)
    assert result.allowed is False
    assert "allowed_symbols" in result.reason


def test_websocket_unhealthy_blocks_new_position():
    result = make_risk(health={"stream_healthy": False}).check_order(symbol="BTCUSDT", side="BUY", quantity=1, price=10)
    assert result.allowed is False
    assert "unhealthy" in result.reason


@pytest.mark.asyncio
async def test_dry_run_order_does_not_call_rest(tmp_path):
    store = CryptoDuckDBStore(str(tmp_path / "risk.db"))
    store.init_schema()
    manager = OrderManager(FailingRESTClient(), make_risk(store=store), store, dry_run=True, strategy_name="demo_strategy")
    result = await manager.create_limit_order(symbol="BTCUSDT", side="BUY", quantity=0.001, price=10000)
    assert result["dry_run"] is True
    assert result["request"]["newClientOrderId"].startswith("oq_demo_strategy_BTCUSDT_")


def test_rest_signature_is_hmac_sha256():
    client = BinanceFuturesRESTClient("key", "secret", "https://example.com")
    assert client._signature("symbol=BTCUSDT&timestamp=1") == "ef9d3d77a34d9a13a21a4c2d7f3e8cb091888a74ca62b5b62f430e78eded95ba"
