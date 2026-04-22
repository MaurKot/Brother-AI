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
    def __init__(self, llm, memory, homeo, neuro, max_questions: int = 30,
                 web=None) -> None:
        self.llm = llm
        self.memory = memory
        self.homeo = homeo
        self.neuro = neuro
        self.max_questions = max_questions
        self.web = web  # optional WebSearch — enables grounded investigation
        self.questions: Deque[OpenQuestion] = deque(maxlen=max_questions)

    def add(self, text: str, weight: float = 0.5) -> None:
        text = text.strip()
        if not text:
            return
        if any(q.text == text for q in self.questions):
            return
        self.questions.append(OpenQuestion(text=text, weight=weight))

    async def ponder_one(self) -> Optional[str]:
        """Take one open question. If web search is wired, ground the answer in real sources."""
        if not self.questions:
            return None
        q = max(self.questions, key=lambda x: x.weight)

        # Try to gather real-world context first.
        evidence = ""
        if self.web is not None:
            try:
                evidence = await self.web.investigate(q.text)
            except Exception:
                evidence = ""

        if evidence:
            prompt = (
                f"Я сам себе задал вопрос: «{q.text}»\n"
                f"Я нашёл в открытых источниках:\n{evidence}\n\n"
                f"Сформулируй для себя короткий вывод (2-3 предложения) от первого лица. "
                f"Если источники противоречат — отметь это. Не говори «согласно источнику»."
            )
            tag = "curiosity_grounded"
        else:
            prompt = (
                f"Я сам себе задал вопрос: «{q.text}»\n"
                f"Подумай и сформулируй гипотезу или направление для ответа в 2-3 предложения. "
                f"Не делай вид, что знаешь — допускай неуверенность."
            )
            tag = "curiosity"

        try:
            ans = (await self.llm.complete(prompt, depth="fast", max_tokens=220)).strip()
        except Exception:
            return None

        if ans:
            mem_text = f"вопрос: {q.text}\nдумаю: {ans}"
            if evidence:
                mem_text += f"\n[оперся на: {evidence[:300]}…]"
            self.memory.save(mem_text, emotion="любопытство",
                             importance=0.65 if evidence else 0.6, tags=[tag])
            self.homeo.apply_event(self.neuro, "new_discovery",
                                   scale=0.7 if evidence else 0.5)
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
