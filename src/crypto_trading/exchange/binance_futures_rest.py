from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import httpx


class BinanceAPIError(RuntimeError):
    def __init__(self, status_code: int, code: int | None, msg: str, endpoint: str):
        super().__init__(f"Binance API error {status_code} {code}: {msg} ({endpoint})")
        self.status_code = status_code
        self.code = code
        self.msg = msg
        self.endpoint = endpoint


class BinanceFuturesRESTClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://testnet.binancefuture.com", timeout: float = 10.0, recv_window: int = 5000) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout, headers={"X-MBX-APIKEY": api_key} if api_key else {})

    async def close(self) -> None:
        await self._client.aclose()

    def _signature(self, query_string: str) -> str:
        return hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

    def _signed_params(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {k: v for k, v in (params or {}).items() if v is not None}
        payload["timestamp"] = int(time.time() * 1000)
        payload["recvWindow"] = self.recv_window
        payload["signature"] = self._signature(urlencode(payload, doseq=True))
        return payload

    async def _request(self, method: str, endpoint: str, *, params: dict[str, Any] | None = None, signed: bool = False) -> dict[str, Any] | list[dict[str, Any]]:
        response = await self._client.request(method, endpoint, params=self._signed_params(params) if signed else params)
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {"msg": response.text}
            raise BinanceAPIError(response.status_code, payload.get("code"), payload.get("msg", "unknown error"), endpoint)
        return response.json()

    async def start_user_data_stream(self) -> str:
        payload = await self._request("POST", "/fapi/v1/listenKey")
        return str(payload["listenKey"])

    async def keepalive_user_data_stream(self) -> dict[str, Any]:
        return dict(await self._request("PUT", "/fapi/v1/listenKey"))

    async def close_user_data_stream(self) -> dict[str, Any]:
        return dict(await self._request("DELETE", "/fapi/v1/listenKey"))

    async def get_account_info(self) -> dict[str, Any]:
        return dict(await self._request("GET", "/fapi/v2/account", signed=True))

    async def get_position_risk(self, symbol: str | None = None) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/fapi/v2/positionRisk", params={"symbol": symbol}, signed=True)
        return list(payload) if isinstance(payload, list) else [payload]

    async def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/fapi/v1/openOrders", params={"symbol": symbol}, signed=True)
        return list(payload) if isinstance(payload, list) else [payload]

    async def create_order(self, *, symbol: str, side: str, type: str, quantity: float, price: float | None = None, timeInForce: str | None = None, reduceOnly: bool | None = None, positionSide: str | None = None, newClientOrderId: str | None = None) -> dict[str, Any]:
        params = {"symbol": symbol, "side": side, "type": type, "quantity": quantity, "price": price, "timeInForce": timeInForce, "reduceOnly": "true" if reduceOnly else None, "positionSide": positionSide, "newClientOrderId": newClientOrderId}
        return dict(await self._request("POST", "/fapi/v1/order", params=params, signed=True))

    async def cancel_order(self, symbol: str, order_id: int | None = None, client_order_id: str | None = None) -> dict[str, Any]:
        return dict(await self._request("DELETE", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id, "origClientOrderId": client_order_id}, signed=True))

    async def get_server_time(self) -> dict[str, Any]:
        return dict(await self._request("GET", "/fapi/v1/time"))
