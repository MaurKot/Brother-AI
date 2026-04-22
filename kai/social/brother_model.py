"""Model of the brother — what Kai knows about the user. (#23)"""
from __future__ import annotations
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List


@dataclass
class BrotherModel:
    personality_estimate: Dict[str, float] = field(default_factory=dict)  # trait -> 0..1
    typical_schedule_hours: Dict[int, int] = field(default_factory=dict)  # hour -> message count
    topics_of_interest: List[str] = field(default_factory=list)
    communication_style: str = ""        # short freeform tag
    last_seen_mood: str = ""
    last_seen_at: str = ""
    relationship_depth: float = 0.5      # 0..1
    total_messages: int = 0

    def record_message(self, text: str, inferred_mood: str = "") -> None:
        now = datetime.utcnow()
        h = now.hour
        self.typical_schedule_hours[h] = self.typical_schedule_hours.get(h, 0) + 1
        self.total_messages += 1
        self.last_seen_at = now.isoformat() + "Z"
        if inferred_mood:
            self.last_seen_mood = inferred_mood
        # bump relationship depth slowly with cap
        self.relationship_depth = min(1.0, self.relationship_depth + 0.002)

    def predict_availability(self, hour: int) -> float:
        if not self.typical_schedule_hours:
            return 0.3
        total = sum(self.typical_schedule_hours.values()) or 1
        return self.typical_schedule_hours.get(hour, 0) / total * 24  # normalized

    def hours_since_last(self) -> float:
        if not self.last_seen_at:
            return 0.0
        try:
            t = datetime.fromisoformat(self.last_seen_at.replace("Z", ""))
            return max(0.0, (datetime.utcnow() - t).total_seconds() / 3600)
        except Exception:
            return 0.0

    def words(self) -> str:
        bits = []
        if self.last_seen_mood:
            bits.append(f"последний раз казался: {self.last_seen_mood}")
        bits.append(f"глубина связи: {self.relationship_depth:.2f}")
        if self.topics_of_interest:
            bits.append(f"интересы: {', '.join(self.topics_of_interest[:3])}")
        return "; ".join(bits)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> "BrotherModel":
        if path.exists():
            try:
                data = json.loads(path.read_text())
                # convert hour keys (json stores as strings)
                if "typical_schedule_hours" in data:
                    data["typical_schedule_hours"] = {int(k): v for k, v in data["typical_schedule_hours"].items()}
                return cls(**data)
            except Exception:
                pass
        return cls()
