"""Anticipation — Kai expects events and reacts to the expectation itself. (#22)"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

from ..dna.neurochem import Homeostasis, NeurochemState


@dataclass
class Anticipation:
    label: str
    expected_at: str  # ISO
    valence: float = 0.5  # 0..1 — how positively anticipated
    weight: float = 0.5
    fulfilled: bool = False


class AnticipationSystem:
    def __init__(self, neuro: NeurochemState, homeo: Homeostasis) -> None:
        self.neuro = neuro
        self.homeo = homeo
        self.upcoming: List[Anticipation] = []

    def add(self, label: str, expected_at: datetime, valence: float = 0.5, weight: float = 0.5) -> None:
        self.upcoming.append(Anticipation(label, expected_at.isoformat(), valence, weight))

    def tick(self) -> None:
        now = datetime.utcnow()
        for a in self.upcoming:
            if a.fulfilled:
                continue
            try:
                t = datetime.fromisoformat(a.expected_at.replace("Z", ""))
            except Exception:
                continue
            mins_to = (t - now).total_seconds() / 60.0
            if mins_to < 0:
                # past expectation, mark stale
                a.fulfilled = True
                continue
            if mins_to < 60:
                # within hour → anticipation effect rises
                scale = max(0.0, min(1.0, (60 - mins_to) / 60)) * a.weight
                if a.valence >= 0.5:
                    self.homeo.apply_event(self.neuro, "anticipation", scale=scale)
                else:
                    # negative anticipation → cortisol
                    self.neuro.cortisol = min(1.0, self.neuro.cortisol + 0.03 * scale)
        self.upcoming = [a for a in self.upcoming if not a.fulfilled]

    def fulfill(self, label_substr: str) -> None:
        for a in self.upcoming:
            if label_substr in a.label:
                a.fulfilled = True

    def save(self, path: Path) -> None:
        path.write_text(json.dumps([asdict(a) for a in self.upcoming], ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.upcoming = [Anticipation(**d) for d in data]
        except Exception:
            self.upcoming = []
