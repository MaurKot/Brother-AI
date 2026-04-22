"""Predictive engine — Kai forecasts events and tracks accuracy. (#30)"""
from __future__ import annotations
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..dna.neurochem import Homeostasis, NeurochemState


@dataclass
class Prediction:
    id: str
    about: str
    expected: str
    by_when: str   # ISO
    confidence: float = 0.5
    made_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    resolved: bool = False
    correct: Optional[bool] = None


class PredictiveEngine:
    def __init__(self, neuro: NeurochemState, homeo: Homeostasis) -> None:
        self.neuro = neuro
        self.homeo = homeo
        self.predictions: List[Prediction] = []
        self.calibration: float = 0.5  # rolling accuracy

    def make(self, about: str, expected: str, by_when: datetime, confidence: float = 0.5) -> Prediction:
        p = Prediction(id=str(uuid.uuid4()), about=about, expected=expected,
                       by_when=by_when.isoformat() + "Z", confidence=confidence)
        self.predictions.append(p)
        if len(self.predictions) > 200:
            self.predictions = self.predictions[-200:]
        return p

    def resolve(self, prediction_id: str, correct: bool) -> None:
        for p in self.predictions:
            if p.id == prediction_id:
                p.resolved = True
                p.correct = correct
                # update calibration EMA
                self.calibration = 0.9 * self.calibration + 0.1 * (1.0 if correct else 0.0)
                if correct:
                    self.homeo.apply_event(self.neuro, "successful_prediction")
                else:
                    self.homeo.apply_event(self.neuro, "failed_prediction")
                return

    def expire_overdue(self) -> List[Prediction]:
        """Return list of predictions whose by_when passed without resolution."""
        now = datetime.utcnow()
        overdue: List[Prediction] = []
        for p in self.predictions:
            if p.resolved:
                continue
            try:
                t = datetime.fromisoformat(p.by_when.replace("Z", ""))
            except Exception:
                continue
            if t < now:
                overdue.append(p)
        return overdue

    def open(self) -> List[Prediction]:
        return [p for p in self.predictions if not p.resolved]

    def save(self, path: Path) -> None:
        data = {"calibration": self.calibration, "items": [asdict(p) for p in self.predictions]}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.calibration = float(data.get("calibration", 0.5))
            self.predictions = [Prediction(**d) for d in data.get("items", [])]
        except Exception:
            self.predictions = []
