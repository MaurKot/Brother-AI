"""Mood — slower than chemistry, persists for hours. (#16)"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from ..dna.neurochem import NeurochemState


@dataclass
class MoodState:
    valence: float = 0.0    # -1..+1
    arousal: float = 0.4    # 0..1
    stability: float = 0.7  # 0..1 — resistance to change
    label: str = "ровно"
    started_at: str = ""

    def update_from(self, neuro: NeurochemState) -> None:
        # Target valence/arousal from chemistry
        target_valence = (neuro.dopamine + neuro.serotonin + neuro.oxytocin) / 3 * 2 - 1
        target_arousal = (neuro.norepinephrine + neuro.cortisol) / 2
        # Mood resists fast change → blend with stability
        a = 1.0 - self.stability
        new_v = self.valence + a * (target_valence - self.valence)
        new_a = self.arousal + a * (target_arousal - self.arousal)
        new_label = self._label_for(new_v, new_a)
        if new_label != self.label:
            self.started_at = datetime.utcnow().isoformat() + "Z"
        self.valence, self.arousal, self.label = new_v, new_a, new_label

    @staticmethod
    def _label_for(v: float, a: float) -> str:
        if v > 0.4 and a > 0.5: return "приподнято"
        if v > 0.4 and a <= 0.5: return "тепло"
        if v < -0.4 and a > 0.5: return "напряжённо"
        if v < -0.4 and a <= 0.5: return "уныло"
        return "ровно"

    def duration_hours(self) -> float:
        if not self.started_at:
            return 0.0
        try:
            t = datetime.fromisoformat(self.started_at.replace("Z", ""))
            return max(0.0, (datetime.utcnow() - t).total_seconds() / 3600)
        except Exception:
            return 0.0

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, path: Path) -> "MoodState":
        if path.exists():
            try:
                return cls(**json.loads(path.read_text()))
            except Exception:
                pass
        return cls(started_at=datetime.utcnow().isoformat() + "Z")
