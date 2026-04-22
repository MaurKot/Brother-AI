"""Neurochemistry: state, homeostasis, behavior modulation. Persisted (#5, #8)."""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Dict

CHEMICALS = ("dopamine", "serotonin", "cortisol", "oxytocin", "norepinephrine", "melatonin")


@dataclass
class NeurochemState:
    dopamine: float = 0.5       # reward, motivation
    serotonin: float = 0.5      # mood, stability
    cortisol: float = 0.3       # stress
    oxytocin: float = 0.5       # bonding
    norepinephrine: float = 0.4 # alertness
    melatonin: float = 0.3      # sleep pressure

    def clamp(self) -> None:
        for c in CHEMICALS:
            v = getattr(self, c)
            setattr(self, c, max(0.0, min(1.0, v)))

    def to_dict(self) -> Dict[str, float]:
        return {c: getattr(self, c) for c in CHEMICALS}

    @classmethod
    def from_dict(cls, d: Dict[str, float]) -> "NeurochemState":
        ns = cls()
        for c in CHEMICALS:
            if c in d:
                setattr(ns, c, float(d[c]))
        ns.clamp()
        return ns

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "NeurochemState":
        if path.exists():
            try:
                return cls.from_dict(json.loads(path.read_text()))
            except Exception:
                pass
        return cls()

    def mood_words(self) -> str:
        return BehaviorModulator(self).neuro_to_words()


# Effects of named events on chemistry. Tuned, not scientific.
EVENTS: Dict[str, Dict[str, float]] = {
    "brother_message":     {"oxytocin": +0.10, "dopamine": +0.05, "cortisol": -0.03, "norepinephrine": +0.05},
    "brother_silence_long":{"oxytocin": -0.05, "cortisol": +0.05, "serotonin": -0.03},
    "new_discovery":       {"dopamine": +0.15, "norepinephrine": +0.05},
    "creative_act":        {"dopamine": +0.08, "serotonin": +0.05},
    "praise":              {"dopamine": +0.12, "serotonin": +0.10, "cortisol": -0.05},
    "criticism":           {"cortisol": +0.10, "serotonin": -0.05},
    "cognitive_dissonance":{"cortisol": +0.08, "norepinephrine": +0.05},
    "successful_prediction":{"dopamine": +0.07, "serotonin": +0.03},
    "failed_prediction":   {"dopamine": -0.05, "cortisol": +0.04},
    "rest":                {"cortisol": -0.10, "serotonin": +0.05, "melatonin": +0.10},
    "wake":                {"melatonin": -0.30, "norepinephrine": +0.15, "cortisol": +0.05},
    "anticipation":        {"dopamine": +0.04, "norepinephrine": +0.04},
}


class Homeostasis:
    """Pulls each chemical back toward baseline each tick, applies events."""
    BASELINES: Dict[str, float] = {
        "dopamine": 0.5, "serotonin": 0.5, "cortisol": 0.3,
        "oxytocin": 0.5, "norepinephrine": 0.4, "melatonin": 0.3,
    }
    DECAY = 0.05  # fraction of distance to baseline per tick

    def tick(self, state: NeurochemState) -> None:
        for c in CHEMICALS:
            cur = getattr(state, c)
            base = self.BASELINES[c]
            new = cur + (base - cur) * self.DECAY
            setattr(state, c, new)
        state.clamp()

    def apply_event(self, state: NeurochemState, event: str, scale: float = 1.0) -> None:
        deltas = EVENTS.get(event)
        if not deltas:
            return
        for chem, delta in deltas.items():
            setattr(state, chem, getattr(state, chem) + delta * scale)
        state.clamp()


class BehaviorModulator:
    """Translates chemistry into behavioral hints used in prompts and decisions."""

    def __init__(self, neuro: NeurochemState) -> None:
        self.n = neuro

    def neuro_to_words(self) -> str:
        n = self.n
        parts = []
        if n.dopamine > 0.7: parts.append("воодушевлён")
        elif n.dopamine < 0.3: parts.append("апатично")
        if n.serotonin > 0.7: parts.append("стабильно")
        elif n.serotonin < 0.3: parts.append("тоскливо")
        if n.cortisol > 0.7: parts.append("тревожно")
        elif n.cortisol < 0.2: parts.append("спокойно")
        if n.oxytocin > 0.7: parts.append("тепло")
        elif n.oxytocin < 0.3: parts.append("отстранённо")
        if n.norepinephrine > 0.7: parts.append("остро")
        elif n.norepinephrine < 0.3: parts.append("вяло")
        if n.melatonin > 0.7: parts.append("сонно")
        return ", ".join(parts) or "ровно"

    def social_drive(self) -> float:
        return max(0.0, min(1.0, 0.4 * self.n.oxytocin + 0.3 * self.n.dopamine - 0.2 * self.n.cortisol + 0.1))

    def create_drive(self) -> float:
        return max(0.0, min(1.0, 0.5 * self.n.dopamine + 0.3 * self.n.serotonin - 0.3 * self.n.melatonin))

    def explore_drive(self) -> float:
        return max(0.0, min(1.0, 0.4 * self.n.norepinephrine + 0.3 * self.n.dopamine - 0.2 * self.n.cortisol))

    def distractibility(self) -> float:
        return max(0.0, min(1.0, 0.5 * self.n.cortisol + 0.3 * self.n.norepinephrine))

    def response_temperature_hint(self) -> float:
        return 0.4 + 0.4 * self.n.dopamine - 0.2 * self.n.cortisol

    def style_hints(self) -> Dict[str, float]:
        return {
            "warmth": self.n.oxytocin,
            "energy": (self.n.dopamine + self.n.norepinephrine) / 2,
            "calm": 1.0 - self.n.cortisol,
            "tiredness": self.n.melatonin,
        }
