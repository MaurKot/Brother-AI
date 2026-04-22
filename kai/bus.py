"""EventBus — async pub/sub. (#43)"""
from __future__ import annotations
import asyncio
import inspect
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List

Handler = Callable[[Dict[str, Any]], Any]


class EventBus:
    def __init__(self) -> None:
        self._subs: Dict[str, List[Handler]] = defaultdict(list)

    def subscribe(self, event: str, handler: Handler) -> None:
        self._subs[event].append(handler)

    async def publish(self, event: str, data: Dict[str, Any] | None = None) -> None:
        data = data or {}
        for h in list(self._subs.get(event, [])):
            try:
                res = h(data)
                if inspect.isawaitable(res):
                    await res
            except Exception as e:  # noqa: BLE001
                # never let a subscriber kill the bus
                from .logger import logger
                logger.error("bus", f"handler error on '{event}': {e!r}")
