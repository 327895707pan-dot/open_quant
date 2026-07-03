from __future__ import annotations

import asyncio
import inspect
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from crypto_trading.events.models import BaseEvent, ListenKeyExpiredEvent, UnknownEvent

Handler = Callable[[BaseEvent], Awaitable[None] | None]

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._queue: asyncio.Queue[BaseEvent] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self.system_health: dict[str, Any] = {
            "websocket_connected": False,
            "last_event_time": None,
            "stream_healthy": False,
        }

    def register(self, event_type: str, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def unregister(self, event_type: str, handler: Handler) -> None:
        if handler in self._handlers.get(event_type, []):
            self._handlers[event_type].remove(handler)

    async def publish(self, event: BaseEvent) -> None:
        await self._queue.put(event)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="crypto-event-bus")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            await self._queue.put(BaseEvent("__STOP__", None, None, {}))
            await self._task
            self._task = None

    async def _run(self) -> None:
        while self._running:
            event = await self._queue.get()
            if event.event_type == "__STOP__":
                break
            await self._dispatch(event)

    async def _dispatch(self, event: BaseEvent) -> None:
        self.system_health["last_event_time"] = event.event_time
        if isinstance(event, ListenKeyExpiredEvent):
            self.system_health["stream_healthy"] = False
            self.system_health["websocket_connected"] = False
        if isinstance(event, UnknownEvent):
            logger.info("Ignoring unknown event type: %s", event.event_type)

        handlers = [*self._handlers.get(event.event_type, []), *self._handlers.get("*", [])]
        for handler in handlers:
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Event handler failed for %s", event.event_type)
