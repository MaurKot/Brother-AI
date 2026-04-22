"""Belief system with Bayesian-ish updating + contradiction detection. (#17, #29)"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Belief:
    text: str
    confidence: float = 0.5  # 0..1
    evidence_count: int = 1
    related_to: str = ""     # subject (e.g. "брат", "мир", "я")
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class BeliefSystem:
    def __init__(self) -> None:
        self.beliefs: Dict[str, Belief] = {}

    def add_or_strengthen(self, text: str, related_to: str = "", direction: float = +1.0, weight: float = 0.1) -> Belief:
        """direction: +1 supports belief, -1 contradicts. weight: 0..1 how strong the evidence."""
        key = text.strip().lower()
        b = self.beliefs.get(key)
        if not b:
            b = Belief(text=text, confidence=0.5, evidence_count=0, related_to=related_to)
            self.beliefs[key] = b
        # Bayesian-ish update
        delta = direction * weight * (1.0 - abs(b.confidence - 0.5) * 0.5)
        b.confidence = max(0.05, min(0.95, b.confidence + delta))
        b.evidence_count += 1
        b.last_updated = datetime.utcnow().isoformat() + "Z"
        if related_to and not b.related_to:
            b.related_to = related_to
        return b

    def about(self, subject: str, top_n: int = 5) -> List[Belief]:
        items = [b for b in self.beliefs.values() if b.related_to == subject]
        items.sort(key=lambda b: -b.confidence)
        return items[:top_n]

    def all_strong(self, min_conf: float = 0.7) -> List[Belief]:
        return sorted(
            [b for b in self.beliefs.values() if b.confidence >= min_conf],
            key=lambda b: -b.confidence,
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({k: asdict(v) for k, v in self.beliefs.items()}, ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.beliefs = {k: Belief(**v) for k, v in data.items()}
        except Exception:
            self.beliefs = {}


class ContradictionDetector:
    """Cheap heuristic: flag belief pairs that mention same subject with opposing words."""
    OPPOSITES = [
        ("любит", "не любит"), ("устаёт", "бодр"), ("молчалив", "разговорчив"),
        ("грустит", "радуется"), ("открыт", "закрыт"),
    ]

    def find_conflicts(self, new_text: str, existing: List[Belief]) -> List[Belief]:
        new_low = new_text.lower()
        conflicts: List[Belief] = []
        for b in existing:
            low = b.text.lower()
            for pos, neg in self.OPPOSITES:
                if (pos in new_low and neg in low) or (neg in new_low and pos in low):
                    conflicts.append(b)
                    break
        return conflicts
