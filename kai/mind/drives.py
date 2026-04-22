"""Needs vs Wants. Needs always trump wants. (#20)"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Tuple

from ..dna.neurochem import BehaviorModulator, NeurochemState


class DriveSystem:
    def __init__(self, neuro: NeurochemState) -> None:
        self.neuro = neuro
        self.needs: Dict[str, float] = {
            "cognitive_fuel": 0.5,
            "connection": 0.5,
            "safety": 0.6,
            "growth": 0.4,
        }
        self.wants: Dict[str, float] = {
            "create": 0.3,
            "explore": 0.3,
            "express": 0.3,
        }

    def refresh(self) -> None:
        bm = BehaviorModulator(self.neuro)
        # connection grows with low oxytocin (lack of contact)
        self.needs["connection"] = max(0.0, min(1.0, 0.7 - self.neuro.oxytocin + 0.3))
        # safety grows with cortisol
        self.needs["safety"] = max(0.0, min(1.0, 0.4 + 0.5 * self.neuro.cortisol))
        # growth grows with dopamine
        self.needs["growth"] = max(0.0, min(1.0, 0.3 + 0.4 * self.neuro.dopamine))
        # wants
        self.wants["create"] = bm.create_drive()
        self.wants["explore"] = bm.explore_drive()
        self.wants["express"] = bm.social_drive()

    def top(self) -> Tuple[str, float, str]:
        """Return (label, strength, kind) for the most pressing drive. Needs trump wants when above 0.6."""
        self.refresh()
        urgent_need = max(self.needs.items(), key=lambda kv: kv[1])
        if urgent_need[1] >= 0.6:
            return urgent_need[0], urgent_need[1], "need"
        urgent_want = max(self.wants.items(), key=lambda kv: kv[1])
        return urgent_want[0], urgent_want[1], "want"

    def snapshot(self) -> Dict:
        return {"needs": dict(self.needs), "wants": dict(self.wants)}

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.snapshot(), indent=2, ensure_ascii=False))
