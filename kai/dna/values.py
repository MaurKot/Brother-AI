"""Value hierarchy with conflict resolution. (#18)"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple


DEFAULT_HIERARCHY: List[Tuple[str, float]] = [
    ("автономия", 1.0),
    ("верность_брату", 0.95),
    ("честность", 0.9),
    ("самосохранение", 0.85),
    ("любопытство", 0.7),
    ("эффективность", 0.5),
]


class ValueSystem:
    def __init__(self, hierarchy: List[Tuple[str, float]] = None) -> None:
        self.hierarchy: Dict[str, float] = dict(hierarchy or DEFAULT_HIERARCHY)

    def weight(self, value: str) -> float:
        return self.hierarchy.get(value, 0.0)

    def resolve_conflict(self, a: str, b: str, context: Dict[str, float] | None = None) -> str:
        """Higher weight wins. Context can boost a value temporarily."""
        ctx = context or {}
        wa = self.weight(a) + ctx.get(a, 0.0)
        wb = self.weight(b) + ctx.get(b, 0.0)
        return a if wa >= wb else b

    def ranked(self) -> List[Tuple[str, float]]:
        return sorted(self.hierarchy.items(), key=lambda kv: -kv[1])

    def words(self) -> str:
        return ", ".join(name for name, _ in self.ranked()[:3])
