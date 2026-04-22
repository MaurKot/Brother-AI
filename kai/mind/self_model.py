"""Self-model — Kai's view of itself. Updated in background, not synchronously. (#11, #12)"""
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Optional

from ..dna.neurochem import BehaviorModulator
from ..logger import logger


class SelfModel:
    """Lightweight rolling self-summary. Updated as a background task to not block messages."""

    def __init__(self, neuro, memory, beliefs, mood, identity, temperament, values) -> None:
        self.neuro = neuro
        self.memory = memory
        self.beliefs = beliefs
        self.mood = mood
        self.identity = identity
        self.temperament = temperament
        self.values = values
        self.summary: str = ""
        self.last_update: Optional[datetime] = None
        self._lock = asyncio.Lock()

    def schedule_update(self) -> None:
        # Fire-and-forget; if one is already running, skip.
        if self._lock.locked():
            return
        asyncio.create_task(self._update_async())

    async def _update_async(self) -> None:
        async with self._lock:
            try:
                bm = BehaviorModulator(self.neuro)
                strong = self.beliefs.all_strong(min_conf=0.7)[:5]
                bel_lines = "; ".join(b.text for b in strong) or "(пока нет твёрдых убеждений)"
                self.summary = (
                    f"Я — {self.identity.name}, {self.identity.days_alive()} дней. "
                    f"Темперамент: {self.temperament.words()}. "
                    f"Ценности: {self.values.words()}. "
                    f"Сейчас: {bm.neuro_to_words()}; настроение: {self.mood.label}. "
                    f"Убеждения: {bel_lines}."
                )
                self.last_update = datetime.utcnow()
            except Exception as e:  # noqa: BLE001
                logger.error("self_model", f"update failed: {e!r}")

    def text(self) -> str:
        return self.summary or "Я — Kai. Ещё формируюсь."
