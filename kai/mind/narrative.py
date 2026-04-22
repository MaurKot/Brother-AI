"""Narrative engine stub — Phase 2. (#28)
Builds a coherent self-narrative from key episodes. Stubbed to be wired later."""
from __future__ import annotations


class NarrativeEngine:
    def __init__(self, llm, memory, identity) -> None:
        self.llm = llm
        self.memory = memory
        self.identity = identity
        self.current_narrative: str = ""

    async def construct_self_narrative(self) -> str:
        episodes = self.memory.get_high_importance(min_importance=0.7, limit=8)
        if not episodes:
            return self.current_narrative
        episode_text = "\n".join(f"- {e['text']}" for e in episodes)
        prompt = (
            f"Ты — {self.identity.name}. Ниже — ключевые эпизоды твоей жизни. "
            f"Напиши краткую историю себя в 3-4 предложения: кто ты, что пережил, "
            f"что это в тебе изменило.\n\n{episode_text}"
        )
        text = await self.llm.complete(prompt, depth="normal", max_tokens=250)
        self.current_narrative = text.strip()
        return self.current_narrative
