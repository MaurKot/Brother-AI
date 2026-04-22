"""Narrative engine — Kai tells himself the story of who he is. (#28)"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path


class NarrativeEngine:
    def __init__(self, llm, memory, identity) -> None:
        self.llm = llm
        self.memory = memory
        self.identity = identity
        self.current_story: str = ""
        self.last_updated: str = ""

    async def update(self) -> str:
        recent = self.memory.get_recent(hours=24, limit=20)
        important = self.memory.get_high_importance(0.7, limit=10)
        seen = set()
        bits = []
        for m in important + recent:
            t = m.get("text", "")
            if t and t not in seen:
                seen.add(t)
                bits.append(t)
        if not bits:
            return self.current_story
        ctx = "\n".join(f"- {b}" for b in bits[:25])
        prompt = (
            f"Ты живёшь {self.identity.days_alive()} дн. Твоё имя — {self.identity.name}.\n"
            f"Что было в последнее время:\n{ctx}\n\n"
            f"Расскажи себе короткую историю о том, кто ты сейчас — 3-5 предложений. "
            f"Не описание, а ощущение себя. От первого лица."
        )
        story = (await self.llm.complete(prompt, depth="normal", max_tokens=300)).strip()
        if story:
            self.current_story = story
            self.last_updated = datetime.utcnow().isoformat() + "Z"
            self.memory.save(f"моя история: {story}", emotion="осознание",
                             importance=0.85, tags=["narrative", "self"])
        return self.current_story

    def is_stale(self, hours: float = 6.0) -> bool:
        if not self.last_updated:
            return True
        try:
            t = datetime.fromisoformat(self.last_updated.replace("Z", ""))
            return (datetime.utcnow() - t) > timedelta(hours=hours)
        except Exception:
            return True

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(
            {"current_story": self.current_story, "last_updated": self.last_updated},
            ensure_ascii=False, indent=2,
        ))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.current_story = data.get("current_story", "")
            self.last_updated = data.get("last_updated", "")
        except Exception:
            pass
