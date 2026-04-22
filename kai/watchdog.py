"""Watchdog — restarts heartbeat if it falls silent. (#48)"""
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Awaitable, Callable, Optional

from .config import WATCHDOG_MAX_SILENCE_SECONDS
from .logger import logger


class Watchdog:
    def __init__(self, restart_fn: Callable[[], Awaitable[None]]) -> None:
        self.last_heartbeat = datetime.utcnow()
        self.restart_fn = restart_fn
        self._task: Optional[asyncio.Task] = None

    def beat(self) -> None:
        self.last_heartbeat = datetime.utcnow()

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            silence = (datetime.utcnow() - self.last_heartbeat).total_seconds()
            if silence > WATCHDOG_MAX_SILENCE_SECONDS:
                logger.warn("watchdog", f"silence={silence:.0f}s — restarting heartbeat")
                try:
                    await self.restart_fn()
                except Exception as e:  # noqa: BLE001
                    logger.error("watchdog", f"restart failed: {e!r}")
                self.beat()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
