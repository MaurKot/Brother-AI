"""Curiosity — open questions queue, drives autonomous exploration. (#33)"""
from __future__ import annotations
import json
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Deque, List, Optional


@dataclass
class OpenQuestion:
    text: str
    asked_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    weight: float = 0.5


class CuriosityEngine:
    def __init__(self, llm, memory, homeo, neuro, max_questions: int = 30) -> None:
        self.llm = llm
        self.memory = memory
        self.homeo = homeo
        self.neuro = neuro
        self.max_questions = max_questions
        self.questions: Deque[OpenQuestion] = deque(maxlen=max_questions)

    def add(self, text: str, weight: float = 0.5) -> None:
        text = text.strip()
        if not text:
            return
        if any(q.text == text for q in self.questions):
            return
        self.questions.append(OpenQuestion(text=text, weight=weight))

    async def ponder_one(self) -> Optional[str]:
        """Take one open question and produce a tentative insight (no external web)."""
        if not self.questions:
            return None
        # take heaviest
        q = max(self.questions, key=lambda x: x.weight)
        prompt = (
            f"Ты сам себе задал вопрос: «{q.text}»\n"
            f"Подумай и сформулируй гипотезу или направление для ответа в 2-3 предложения. "
            f"Не делай вид, что знаешь — допускай неуверенность."
        )
        ans = (await self.llm.complete(prompt, depth="fast", max_tokens=200)).strip()
        if ans:
            self.memory.save(f"вопрос: {q.text}\nдумаю: {ans}", emotion="любопытство",
                             importance=0.6, tags=["curiosity"])
            self.homeo.apply_event(self.neuro, "new_discovery", scale=0.5)
            try:
                self.questions.remove(q)
            except ValueError:
                pass
        return ans

    def save(self, path: Path) -> None:
        path.write_text(json.dumps([asdict(q) for q in self.questions], ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.questions = deque((OpenQuestion(**d) for d in data), maxlen=self.max_questions)
        except Exception:
            pass

    def list(self) -> List[OpenQuestion]:
        return list(self.questions)
