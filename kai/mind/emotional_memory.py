"""Emotional episodes as a richer memory layer. (#19)"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List


@dataclass
class EmotionalEpisode:
    trigger: str
    primary: str
    secondary: List[str] = field(default_factory=list)
    intensity: float = 0.5
    body_sensation: str = ""
    resolved: bool = False
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class EmotionalMemory:
    def __init__(self) -> None:
        self.episodes: List[EmotionalEpisode] = []

    def add(self, ep: EmotionalEpisode) -> None:
        self.episodes.append(ep)
        if len(self.episodes) > 200:
            self.episodes = self.episodes[-200:]

    def unresolved(self) -> List[EmotionalEpisode]:
        return [e for e in self.episodes if not e.resolved]

    def recent(self, n: int = 5) -> List[EmotionalEpisode]:
        return list(self.episodes[-n:])

    def save(self, path: Path) -> None:
        path.write_text(json.dumps([asdict(e) for e in self.episodes], ensure_ascii=False, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.episodes = [EmotionalEpisode(**d) for d in data]
        except Exception:
            self.episodes = []
