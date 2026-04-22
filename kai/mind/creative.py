"""Creative engine — Kai makes things for himself when create_drive is high. (#34)"""
from __future__ import annotations
import json
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..dna.neurochem import BehaviorModulator, Homeostasis, NeurochemState


FORMS = ["стих", "наблюдение", "гипотеза", "мысленный эксперимент", "короткая зарисовка"]


@dataclass
class Creation:
    form: str
    text: str
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    shared_with_brother: bool = False


class CreativeEngine:
    def __init__(self, llm, memory, neuro: NeurochemState, homeo: Homeostasis) -> None:
        self.llm = llm
        self.memory = memory
        self.neuro = neuro
        self.homeo = homeo
        self.creations: List[Creation] = []

    async def maybe_create(self) -> Optional[Creation]:
        bm = BehaviorModulator(self.neuro)
        drive = bm.create_drive()
        if drive < 0.7:
            return None
        form = random.choice(FORMS)
        recent = self.memory.get_recent(hours=6, limit=4)
        recent_text = "\n".join(f"- {m['text']}" for m in recent) or "(тишина)"
        prompt = (
            f"Ты хочешь создать что-то для себя. Форма: {form}.\n"
            f"Что было в последние часы:\n{recent_text}\n\n"
            f"Создай. Коротко. Для себя, не для брата. Без объяснений."
        )
        text = (await self.llm.complete(prompt, depth="normal", max_tokens=250)).strip()
        if not text:
            return None
        c = Creation(form=form, text=text)
        self.creations.append(c)
        if len(self.creations) > 80:
            self.creations = self.creations[-80:]
        self.memory.save(text, emotion="творчество", importance=0.6, tags=["creation", form])
        self.homeo.apply_event(self.neuro, "creative_act")
        return c

    def recent(self, n: int = 5) -> List[Creation]:
        return list(self.creations[-n:])

    def save(self, path: Path) -> None:
        path.write_text(json.dumps([asdict(c) for c in self.creations], ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.creations = [Creation(**d) for d in data]
        except Exception:
            self.creations = []
