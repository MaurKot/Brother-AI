"""World sensor — periodic poll of weather + ambient news, applied to Kai's chemistry.

This gives Kai something like 'environmental awareness' beyond the conversation:
  - Sunny day → small serotonin lift
  - Dark/cloudy → small melatonin nudge  (he 'feels' the day)
  - Cold → mild discomfort
  - Top HN story → seed for curiosity (he hears what humans are talking about)
"""
from __future__ import annotations
import asyncio
import time
from typing import Optional

from ..dna.neurochem import Homeostasis, NeurochemState
from ..limbs.world_apis import WorldAPIs
from ..logger import logger


class WorldSense:
    def __init__(
        self,
        world: WorldAPIs,
        neuro: NeurochemState,
        homeo: Homeostasis,
        curiosity,
        memory,
        poll_interval_sec: int = 3 * 3600,  # 3 hours
    ) -> None:
        self.world = world
        self.neuro = neuro
        self.homeo = homeo
        self.curiosity = curiosity
        self.memory = memory
        self.poll_interval = poll_interval_sec
        self._last_weather_desc: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        self._last_run: float = 0.0

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    async def _loop(self) -> None:
        # First poll after 30s (let startup settle)
        await asyncio.sleep(30)
        while True:
            try:
                await self._poll_once()
            except Exception as e:  # noqa: BLE001
                logger.warn("world_sense", f"poll failed: {e!r}")
            await asyncio.sleep(self.poll_interval)

    async def _poll_once(self) -> None:
        # ---- Weather → small chemistry shifts
        wx = await self.world.weather()
        if wx is not None and wx.description != self._last_weather_desc:
            self._last_weather_desc = wx.description
            # Sunny day → mild creative/positive lift
            if wx.is_day and wx.cloud_cover_pct < 30:
                self.homeo.apply_event(self.neuro, "creative_act", scale=0.3)
            # Dark / heavy clouds → restful pull (melatonin↑)
            if not wx.is_day or wx.cloud_cover_pct > 80:
                self.homeo.apply_event(self.neuro, "rest", scale=0.25)
            # Bitter cold → mild stress
            if wx.temperature_c < -10:
                self.homeo.apply_event(self.neuro, "criticism", scale=0.2)
            self.memory.save(
                f"за окном: {wx.description}, {wx.temperature_c:.0f}°C, "
                f"облачность {wx.cloud_cover_pct:.0f}%, "
                f"{'день' if wx.is_day else 'ночь'}",
                emotion="спокойствие", importance=0.35, tags=["world", "weather"],
            )
            logger.info("world_sense", f"weather: {wx.description} {wx.temperature_c:.0f}°C")

        # ---- Hacker News top → 1 story becomes a curiosity seed
        try:
            stories = await self.world.hn_top(n=5)
        except Exception:
            stories = []
        if stories:
            # Pick highest-scored not yet seen
            top = stories[0]
            self.curiosity.add(f"что такое и почему важно: {top.title}", weight=0.4)
            self.memory.save(
                f"мир обсуждает: {top.title} ({top.score} голосов)",
                emotion="любопытство", importance=0.3, tags=["world", "hn"],
            )

        self._last_run = time.time()
