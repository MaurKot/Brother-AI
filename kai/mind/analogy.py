"""Analogies — make new things less scary by finding past parallels. (#31)"""
from __future__ import annotations
from typing import List


class AnalogySystem:
    def __init__(self, llm, memory) -> None:
        self.llm = llm
        self.memory = memory

    async def find(self, situation: str) -> str:
        similar = self.memory.recall(situation, limit=3)
        if not similar:
            return ""
        ctx = "\n".join(f"- {m['text']}" for m in similar)
        prompt = (
            f"Тебе сейчас встретилось: «{situation}». В памяти похожее:\n{ctx}\n\n"
            f"Сформулируй короткую аналогию: «это похоже на …, потому что …». 1-2 предложения."
        )
        return (await self.llm.complete(prompt, depth="fast", max_tokens=120)).strip()
