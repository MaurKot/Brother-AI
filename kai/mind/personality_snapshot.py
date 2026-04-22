"""Personality versioning — daily snapshots for retrospection. (#39)"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class PersonalitySnapshot:
    ts: str
    days_alive: int
    temperament: Dict[str, float]
    values_top: List[str]
    neuro: Dict[str, float]
    mood: str
    top_beliefs: List[str]
    relationship_depth: float


class PersonalityVersioning:
    def __init__(self) -> None:
        self.snapshots: List[PersonalitySnapshot] = []
        self.last_snapshot_date: str = ""

    def maybe_snapshot(self, kai: Any) -> bool:
        today = datetime.utcnow().date().isoformat()
        if today == self.last_snapshot_date:
            return False
        snap = PersonalitySnapshot(
            ts=datetime.utcnow().isoformat() + "Z",
            days_alive=kai.identity.days_alive(),
            temperament={
                "openness": kai.temperament.openness,
                "conscientiousness": kai.temperament.conscientiousness,
                "extraversion": kai.temperament.extraversion,
                "agreeableness": kai.temperament.agreeableness,
                "neuroticism": kai.temperament.neuroticism,
            },
            values_top=[name for name, _ in kai.values.ranked()[:3]],
            neuro=kai.neuro.to_dict(),
            mood=kai.mood.label,
            top_beliefs=[b.text for b in kai.beliefs.all_strong(0.7)[:5]],
            relationship_depth=kai.brother.relationship_depth,
        )
        self.snapshots.append(snap)
        if len(self.snapshots) > 365:
            self.snapshots = self.snapshots[-365:]
        self.last_snapshot_date = today
        return True

    def compare(self, days_back: int = 7) -> Dict[str, Any]:
        if len(self.snapshots) < 2:
            return {}
        latest = self.snapshots[-1]
        older = self.snapshots[max(0, len(self.snapshots) - 1 - days_back)]
        diffs: Dict[str, Any] = {"days_compared": days_back, "temperament_delta": {}}
        for k, v in latest.temperament.items():
            diffs["temperament_delta"][k] = round(v - older.temperament.get(k, v), 4)
        diffs["neuroticism_change_words"] = (
            "стал спокойнее" if diffs["temperament_delta"].get("neuroticism", 0) < 0 else
            "стал тревожнее" if diffs["temperament_delta"].get("neuroticism", 0) > 0 else
            "без изменений в тревожности"
        )
        diffs["depth_delta"] = round(latest.relationship_depth - older.relationship_depth, 4)
        return diffs

    def save(self, path: Path) -> None:
        data = {
            "last_snapshot_date": self.last_snapshot_date,
            "snapshots": [asdict(s) for s in self.snapshots],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.last_snapshot_date = data.get("last_snapshot_date", "")
            self.snapshots = [PersonalitySnapshot(**s) for s in data.get("snapshots", [])]
        except Exception:
            pass
