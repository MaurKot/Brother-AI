"""Graceful shutdown — persists everything before exit. (#14, #46)"""
from __future__ import annotations
import asyncio
from typing import Callable, List

from .logger import logger


class ShutdownManager:
    def __init__(self) -> None:
        self._steps: List[Callable] = []
        self._done = False

    def register(self, step: Callable) -> None:
        self._steps.append(step)

    async def shutdown(self, reason: str = "manual") -> None:
        if self._done:
            return
        self._done = True
        logger.info("shutdown", f"reason={reason}")
        for step in self._steps:
            try:
                res = step()
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:  # noqa: BLE001
                logger.error("shutdown", f"step failed: {e!r}")
