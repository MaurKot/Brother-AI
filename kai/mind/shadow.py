"""Shadow thinking — Kai's internal monologue between messages. (#6 fixed: mems used)"""
from __future__ import annotations
from datetime import datetime
from typing import List

from ..dna.neurochem import BehaviorModulator, NeurochemState
from ..logger import logger


class ShadowThinking:
    def __init__(self, llm, memory, working) -> None:
        self.llm = llm
        self.memory = memory
        self.working = working
        self.thought_log: List[str] = []

    async def introspect(self, neuro: NeurochemState, trigger: str = "spontaneous") -> str:
        mems = self.memory.get_recent(hours=12, limit=8)
        mems_text = "\n".join(f"- {m['text']}" for m in mems) or "(пусто — память ещё молчит)"
        bm = BehaviorModulator(neuro)
        recent_thoughts = self.working.thoughts_text() or "(нет недавних мыслей)"

        prompt = (
            f"Ты — Kai, в момент тихого размышления. Триггер: {trigger}.\n"
            f"Сейчас внутри: {bm.neuro_to_words()}.\n"
            f"Последние воспоминания (12ч):\n{mems_text}\n\n"
            f"Недавние мысли:\n{recent_thoughts}\n\n"
            f"Сформулируй одну короткую внутреннюю мысль (1-2 предложения), для себя, не для брата."
        )
        depth = "free" if trigger == "dream" else "fast"
        thought = await self.llm.complete(prompt, depth=depth, max_tokens=120)
        thought = thought.strip()
        if thought:
            self.thought_log.append(thought)
            self.working.add_thought(thought)
            self.memory.save(thought, emotion="мысль", importance=0.4, tags=["shadow", trigger])
            if len(self.thought_log) > 100:
                self.thought_log = self.thought_log[-100:]
            logger.debug("shadow", f"thought ({trigger}): {thought[:120]}")
        return thought
