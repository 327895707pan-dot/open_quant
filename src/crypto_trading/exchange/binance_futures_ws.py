from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import websockets

from crypto_trading.events.event_bus import EventBus
from crypto_trading.events.models import ListenKeyExpiredEvent
from crypto_trading.events.parser import EventParser
from crypto_trading.exchange.binance_futures_rest import BinanceFuturesRESTClient
from crypto_trading.storage.duckdb_store import CryptoDuckDBStore

logger = logging.getLogger(__name__)


class BinanceFuturesUserDataStream:
    def __init__(self, rest_client: BinanceFuturesRESTClient, store: CryptoDuckDBStore, parser: EventParser, event_bus: EventBus, ws_base_url: str = "wss://fstream.binance.com", keepalive_interval_seconds: int = 1800, reconnect_before_seconds: int = 82800, dry_run: bool = True) -> None:
        self.rest_client = rest_client
        self.store = store
        self.parser = parser
        self.event_bus = event_bus
        self.ws_base_url = ws_base_url.rstrip("/")
        self.keepalive_interval_seconds = keepalive_interval_seconds
        self.reconnect_before_seconds = reconnect_before_seconds
        self.dry_run = dry_run
        self.listen_key: str | None = None
        self._stop_event = asyncio.Event()
        self._keepalive_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._stop_event.clear()
        backoff = 1
        while not self._stop_event.is_set():
            try:
                await self._connect_once()
                backoff = 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("User data stream failed")
                self.event_bus.system_health["stream_healthy"] = False
                self.event_bus.system_health["websocket_connected"] = False
                self.store.insert_stream_status({"status": "disconnected", "message": str(exc), "listen_key": self.listen_key})
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def stop(self) -> None:
        self._stop_event.set()
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None

    async def _connect_once(self) -> None:
        self.listen_key = await self.rest_client.start_user_data_stream()
        url = f"{self.ws_base_url}/private/ws/{self.listen_key}"
        connected_at = time.monotonic()
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        async with websockets.connect(url) as websocket:
            self.event_bus.system_health["websocket_connected"] = True
            self.event_bus.system_health["stream_healthy"] = True
            self.store.insert_stream_status({"status": "connected", "message": "websocket connected", "listen_key": self.listen_key})
            async for message in websocket:
                if self._stop_event.is_set():
                    break
                await self._handle_message(message)
                if time.monotonic() - connected_at >= self.reconnect_before_seconds:
                    self.store.insert_stream_status({"status": "reconnecting", "message": "connection age reached reconnect threshold", "listen_key": self.listen_key})
                    break

    async def _keepalive_loop(self) -> None:
        while not self._stop_event.is_set():
            await asyncio.sleep(self.keepalive_interval_seconds)
            try:
                await self.rest_client.keepalive_user_data_stream()
                self.store.insert_stream_status({"status": "keepalive", "message": "listenKey keepalive", "listen_key": self.listen_key})
            except Exception:
                logger.exception("listenKey keepalive failed")
                self.event_bus.system_health["stream_healthy"] = False

    async def _handle_message(self, message: str | bytes) -> None:
        raw: dict[str, Any] = json.loads(message)
        self.store.insert_raw_event(raw, source="binance_user_data_stream")
        event = self.parser.parse(raw)
        await self.event_bus.publish(event)
        if isinstance(event, ListenKeyExpiredEvent):
            self.store.insert_stream_status({"status": "listen_key_expired", "message": "listenKeyExpired received", "listen_key": self.listen_key, "event_time": event.event_time})
            self.event_bus.system_health["stream_healthy"] = False
            raise RuntimeError("listenKeyExpired received")
