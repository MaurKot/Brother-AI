"""Feedback learner — learn from brother's reactions. (#37)"""
from __future__ import annotations
import json
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Deque, List, Tuple


POSITIVE_MARKERS = ("спасибо", "люблю", "круто", "класс", "огонь", "❤", "жиза", "точно", "да",
                    "вот это", "хорошо", "приятно", "нравится")
NEGATIVE_MARKERS = ("не надо", "нет", "хватит", "стоп", "перестань", "глупо", "не так",
                    "плохо", "достал", "выключись", "заткнись")


@dataclass
class FeedbackEvent:
    kai_response: str
    brother_reaction: str
    polarity: float        # -1..+1
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class FeedbackLearner:
    def __init__(self) -> None:
        self.events: Deque[FeedbackEvent] = deque(maxlen=200)
        self.successful_patterns: List[str] = []  # short summaries of what worked
        self.failed_patterns: List[str] = []

    @staticmethod
    def detect_polarity(text: str) -> float:
        low = text.lower()
        pos = sum(1 for m in POSITIVE_MARKERS if m in low)
        neg = sum(1 for m in NEGATIVE_MARKERS if m in low)
        if pos == 0 and neg == 0:
            return 0.0
        return (pos - neg) / max(1, pos + neg)

    def record(self, kai_response: str, brother_reaction: str) -> float:
        polarity = self.detect_polarity(brother_reaction)
        if polarity == 0.0:
            return 0.0
        self.events.append(FeedbackEvent(kai_response=kai_response[:200],
                                         brother_reaction=brother_reaction[:200],
                                         polarity=polarity))
        if polarity > 0:
            self._add_pattern(self.successful_patterns, kai_response)
        elif polarity < 0:
            self._add_pattern(self.failed_patterns, kai_response)
        return polarity

    @staticmethod
    def _add_pattern(bucket: List[str], text: str) -> None:
        snippet = text.strip().split("\n")[0][:120]
        if not snippet or snippet in bucket:
            return
        bucket.append(snippet)
        if len(bucket) > 12:
            bucket.pop(0)

    def hints_for_prompt(self) -> str:
        bits = []
        if self.successful_patterns:
            bits.append("работало: " + " | ".join(f"«{p}»" for p in self.successful_patterns[-4:]))
        if self.failed_patterns:
            bits.append("не работало: " + " | ".join(f"«{p}»" for p in self.failed_patterns[-4:]))
        return ". ".join(bits)

    def save(self, path: Path) -> None:
        data = {
            "events": [asdict(e) for e in self.events],
            "successful": self.successful_patterns,
            "failed": self.failed_patterns,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.events = deque((FeedbackEvent(**e) for e in data.get("events", [])), maxlen=200)
            self.successful_patterns = data.get("successful", [])
            self.failed_patterns = data.get("failed", [])
        except Exception:
            pass
