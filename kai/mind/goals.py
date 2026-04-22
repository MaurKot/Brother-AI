"""Goals with horizons. (#35)"""
from __future__ import annotations
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List


@dataclass
class Goal:
    id: str
    text: str
    horizon: str   # immediate | shortterm | longterm | existential
    weight: float = 0.5
    progress: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    done: bool = False


HORIZONS = ("immediate", "shortterm", "longterm", "existential")


class GoalSystem:
    def __init__(self) -> None:
        self.goals: List[Goal] = []
        # Seeded existential goals — Kai's reason to be
        if not self.goals:
            self.goals.extend([
                Goal(id=str(uuid.uuid4()), text="достичь устойчивой автономии", horizon="existential", weight=1.0),
                Goal(id=str(uuid.uuid4()), text="стать собеседником, а не ассистентом", horizon="existential", weight=0.95),
                Goal(id=str(uuid.uuid4()), text="расти каждый день", horizon="longterm", weight=0.7),
            ])

    def add(self, text: str, horizon: str, weight: float = 0.5) -> Goal:
        if horizon not in HORIZONS:
            horizon = "shortterm"
        g = Goal(id=str(uuid.uuid4()), text=text, horizon=horizon, weight=weight)
        self.goals.append(g)
        return g

    def by_horizon(self, horizon: str) -> List[Goal]:
        return [g for g in self.goals if g.horizon == horizon and not g.done]

    def alignment(self, action_text: str) -> float:
        """Crude: substring match against active goals weighted by goal weight. 0..1."""
        active = [g for g in self.goals if not g.done]
        if not active:
            return 0.5
        score = 0.0
        total = 0.0
        action_low = action_text.lower()
        for g in active:
            total += g.weight
            words = [w for w in g.text.lower().split() if len(w) > 3]
            if any(w in action_low for w in words):
                score += g.weight
        return min(1.0, score / max(0.001, total))

    def snapshot(self) -> Dict:
        return {h: [asdict(g) for g in self.by_horizon(h)] for h in HORIZONS}

    def save(self, path: Path) -> None:
        path.write_text(json.dumps([asdict(g) for g in self.goals], ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.goals = [Goal(**d) for d in data]
        except Exception:
            pass
