"""Prompt evolution — Kai improves its own internal prompts. (#36)
Light implementation: tracks named prompt variants and their success scores."""
from __future__ import annotations
import json
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class PromptVariant:
    name: str
    text: str
    score: float = 0.0
    uses: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class PromptEvolution:
    def __init__(self, llm) -> None:
        self.llm = llm
        self.variants: Dict[str, List[PromptVariant]] = {}  # bucket name -> variants

    def register(self, bucket: str, name: str, text: str) -> PromptVariant:
        v = PromptVariant(name=name, text=text)
        self.variants.setdefault(bucket, []).append(v)
        return v

    def best(self, bucket: str) -> Optional[PromptVariant]:
        items = self.variants.get(bucket, [])
        if not items:
            return None
        # epsilon-greedy: 15% explore
        if random.random() < 0.15:
            return random.choice(items)
        return max(items, key=lambda v: v.score / max(1, v.uses))

    def reward(self, bucket: str, name: str, signal: float) -> None:
        for v in self.variants.get(bucket, []):
            if v.name == name:
                v.uses += 1
                v.score += signal
                return

    async def mutate(self, bucket: str, base: PromptVariant) -> Optional[PromptVariant]:
        prompt = (
            "Перед тобой шаблон внутреннего промпта. Переформулируй его, чтобы он "
            "был чуть точнее или давал более живой результат. Сохрани смысл и плейсхолдеры. "
            f"Верни только новый текст.\n\nИсходный:\n{base.text}"
        )
        new_text = (await self.llm.complete(prompt, depth="fast", max_tokens=300)).strip()
        if not new_text or new_text == base.text:
            return None
        new_name = f"{base.name}_v{len(self.variants.get(bucket, [])) + 1}"
        return self.register(bucket, new_name, new_text)

    def snapshot(self) -> Dict:
        return {b: [asdict(v) for v in items] for b, items in self.variants.items()}

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.snapshot(), ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.variants = {b: [PromptVariant(**d) for d in items] for b, items in data.items()}
        except Exception:
            pass
