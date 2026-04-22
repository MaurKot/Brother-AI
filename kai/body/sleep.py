"""Sleep cycle. Dreams use 'free' depth so they don't burn budget. (#13)"""
from __future__ import annotations
import asyncio
import random
from datetime import datetime

from ..dna.neurochem import Homeostasis, NeurochemState
from ..logger import logger


class SleepCycle:
    def __init__(self, neuro: NeurochemState, homeo: Homeostasis, shadow) -> None:
        self.neuro = neuro
        self.homeo = homeo
        self.shadow = shadow
        self.is_sleeping = False

    def should_sleep(self) -> bool:
        h = datetime.utcnow().hour
        # crude "night" window — adjust to user TZ later
        in_night = h < 5 or h >= 22
        return in_night and self.neuro.melatonin > 0.6 and not self.is_sleeping

    async def enter_sleep(self) -> None:
        self.is_sleeping = True
        logger.info("sleep", "entering sleep")
        self.homeo.apply_event(self.neuro, "rest")
        # 1-3 dream cycles, all on free depth
        for _ in range(random.randint(1, 3)):
            await self.shadow.introspect(self.neuro, trigger="dream")
            await asyncio.sleep(0.1)
        logger.info("sleep", "sleep cycle done")

    def wake(self) -> None:
        if not self.is_sleeping:
            return
        self.is_sleeping = False
        self.homeo.apply_event(self.neuro, "wake")
        logger.info("sleep", "waking up")
