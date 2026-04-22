"""Mood contagion — Kai partially absorbs brother's emotion. (#24)"""
from __future__ import annotations
import json
from typing import Optional

from ..dna.neurochem import Homeostasis, NeurochemState
from ..logger import logger


# Map LLM-classified emotions → event names in EVENTS table.
EMOTION_TO_EVENT = {
    "радость": "praise",
    "восторг": "praise",
    "тепло": "brother_message",
    "грусть": "criticism",
    "уныние": "criticism",
    "тревога": "cognitive_dissonance",
    "стресс": "cognitive_dissonance",
    "злость": "criticism",
    "усталость": "rest",
    "нейтрально": "brother_message",
}


class MoodContagion:
    def __init__(self, llm, homeo: Homeostasis, neuro: NeurochemState) -> None:
        self.llm = llm
        self.homeo = homeo
        self.neuro = neuro

    async def classify_emotion(self, text: str) -> str:
        prompt = (
            "Определи доминирующую эмоцию в этом сообщении. Ответь одним словом из списка: "
            "радость, восторг, тепло, грусть, уныние, тревога, стресс, злость, усталость, нейтрально.\n\n"
            f"Сообщение: {text}\n\nЭмоция:"
        )
        try:
            resp = await self.llm.complete(prompt, depth="fast", max_tokens=8)
        except Exception as e:  # noqa: BLE001
            logger.warn("contagion", f"classify failed: {e!r}")
            return "нейтрально"
        word = (resp or "нейтрально").strip().lower().split()[0].strip(".,!?")
        return word if word in EMOTION_TO_EVENT else "нейтрально"

    async def apply(self, text: str) -> str:
        emotion = await self.classify_emotion(text)
        contagion_factor = max(0.1, min(0.8, 0.4 * self.neuro.oxytocin + 0.2))
        event = EMOTION_TO_EVENT.get(emotion, "brother_message")
        self.homeo.apply_event(self.neuro, event, scale=contagion_factor)
        logger.debug("contagion", f"emotion={emotion} factor={contagion_factor:.2f} event={event}")
        return emotion
