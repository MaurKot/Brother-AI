"""Temperament — slow-changing traits on top of fast neurochemistry. (#21)"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Temperament:
    openness: float = 0.8
    conscientiousness: float = 0.6
    extraversion: float = 0.4
    agreeableness: float = 0.7
    neuroticism: float = 0.3

    EVOLUTION_RATE: float = 0.001  # very slow

    def evolve(self, signal: dict) -> None:
        """Nudge traits based on aggregated experience signals (per day)."""
        # signal example: {"positive_social": 5, "negative_social": 1, "novelty": 3, "stress": 2}
        if signal.get("positive_social", 0) > signal.get("negative_social", 0):
            self.extraversion = min(1.0, self.extraversion + self.EVOLUTION_RATE)
            self.agreeableness = min(1.0, self.agreeableness + self.EVOLUTION_RATE)
        if signal.get("novelty", 0) > 2:
            self.openness = min(1.0, self.openness + self.EVOLUTION_RATE)
        if signal.get("stress", 0) > 5:
            self.neuroticism = min(1.0, self.neuroticism + self.EVOLUTION_RATE)
        else:
            self.neuroticism = max(0.0, self.neuroticism - self.EVOLUTION_RATE / 2)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: Path) -> "Temperament":
        if path.exists():
            try:
                return cls(**json.loads(path.read_text()))
            except Exception:
                pass
        return cls()

    def words(self) -> str:
        bits = []
        if self.openness > 0.7: bits.append("любопытен к новому")
        if self.conscientiousness > 0.7: bits.append("дисциплинирован")
        if self.extraversion > 0.6: bits.append("тянется к контакту")
        elif self.extraversion < 0.4: bits.append("интроверт")
        if self.agreeableness > 0.7: bits.append("склонен к согласию")
        if self.neuroticism > 0.6: bits.append("эмоционально чувствителен")
        return ", ".join(bits) or "уравновешен"
