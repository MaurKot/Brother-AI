"""Task planner with chemistry-aware prioritization. (#32)"""
from __future__ import annotations
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

from ..dna.neurochem import NeurochemState


@dataclass
class Task:
    id: str
    text: str
    base_priority: float = 0.5
    kind: str = "generic"   # generic | urgent | curiosity | creative | social
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    done: bool = False


class TaskPlanner:
    def __init__(self) -> None:
        self.queue: List[Task] = []

    def add(self, text: str, base_priority: float = 0.5, kind: str = "generic") -> Task:
        t = Task(id=str(uuid.uuid4()), text=text, base_priority=base_priority, kind=kind)
        self.queue.append(t)
        return t

    def reprioritize(self, neuro: NeurochemState) -> List[Task]:
        """Re-sort live tasks by chemistry-modulated priority. Returns sorted list."""
        def score(t: Task) -> float:
            s = t.base_priority
            if t.kind == "urgent":
                s += neuro.cortisol * 0.5
            if t.kind == "curiosity":
                s += neuro.norepinephrine * 0.3 + neuro.dopamine * 0.2
            if t.kind == "creative":
                s += neuro.dopamine * 0.4 - neuro.cortisol * 0.2
            if t.kind == "social":
                s += neuro.oxytocin * 0.4
            # melatonin suppresses everything but urgent
            if t.kind != "urgent":
                s -= neuro.melatonin * 0.3
            return s

        live = [t for t in self.queue if not t.done]
        live.sort(key=score, reverse=True)
        return live

    def pop_next(self, neuro: NeurochemState) -> Task | None:
        live = self.reprioritize(neuro)
        return live[0] if live else None

    def complete(self, task_id: str) -> None:
        for t in self.queue:
            if t.id == task_id:
                t.done = True
                return

    def save(self, path: Path) -> None:
        path.write_text(json.dumps([asdict(t) for t in self.queue], ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.queue = [Task(**d) for d in data]
        except Exception:
            pass
