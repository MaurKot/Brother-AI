"""Meta-learner — track learning velocity and patterns. (#38)"""
from __future__ import annotations
import json
from collections import Counter, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Deque, Dict, Tuple


class MetaLearner:
    def __init__(self) -> None:
        self.belief_growth: Deque[Tuple[str, int]] = deque(maxlen=30)  # (date, total beliefs)
        self.curiosity_resolutions: Deque[Tuple[str, int]] = deque(maxlen=30)

    def record_daily(self, date_iso: str, n_beliefs: int, n_curiosity_resolved: int) -> None:
        if self.belief_growth and self.belief_growth[-1][0] == date_iso:
            self.belief_growth[-1] = (date_iso, n_beliefs)
            self.curiosity_resolutions[-1] = (date_iso, n_curiosity_resolved)
        else:
            self.belief_growth.append((date_iso, n_beliefs))
            self.curiosity_resolutions.append((date_iso, n_curiosity_resolved))

    def velocity(self) -> Dict[str, float]:
        def slope(series: Deque[Tuple[str, int]]) -> float:
            if len(series) < 2:
                return 0.0
            return (series[-1][1] - series[0][1]) / max(1, len(series) - 1)
        return {
            "beliefs_per_day": slope(self.belief_growth),
            "questions_resolved_per_day": slope(self.curiosity_resolutions),
        }

    def words(self) -> str:
        v = self.velocity()
        bits = []
        if v["beliefs_per_day"] > 0.5:
            bits.append("я расту во взглядах")
        elif v["beliefs_per_day"] < 0.05:
            bits.append("новых убеждений почти нет")
        if v["questions_resolved_per_day"] > 0.5:
            bits.append("любопытство активно")
        return "; ".join(bits) or "темп обучения ровный"

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({
            "belief_growth": list(self.belief_growth),
            "curiosity_resolutions": list(self.curiosity_resolutions),
        }, ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.belief_growth = deque(((a, b) for a, b in data.get("belief_growth", [])), maxlen=30)
            self.curiosity_resolutions = deque(((a, b) for a, b in data.get("curiosity_resolutions", [])), maxlen=30)
        except Exception:
            pass
