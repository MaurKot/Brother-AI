"""Linguistic profile — adapt style toward the brother's. (#25)"""
from __future__ import annotations
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict


WORD_RE = re.compile(r"[А-Яа-яЁёA-Za-z]+")
EMOJI_RE = re.compile(
    "["                                      # rough emoji range
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)


@dataclass
class LinguisticProfile:
    vocab_freq: Dict[str, int] = field(default_factory=dict)
    avg_message_length: float = 0.0
    punctuation_density: float = 0.0
    uses_emoji: bool = False
    formality_level: float = 0.5
    sample_count: int = 0

    def observe(self, text: str) -> None:
        if not text:
            return
        words = WORD_RE.findall(text.lower())
        for w in words:
            if len(w) >= 3:
                self.vocab_freq[w] = self.vocab_freq.get(w, 0) + 1
        # rolling avg
        n = self.sample_count
        new_n = n + 1
        msg_len = len(text)
        self.avg_message_length = (self.avg_message_length * n + msg_len) / new_n
        punct = sum(1 for ch in text if ch in ".,!?;:—–-…")
        self.punctuation_density = (self.punctuation_density * n + punct / max(1, msg_len)) / new_n
        if EMOJI_RE.search(text):
            self.uses_emoji = True
        # crude formality: capital letters at start, no slang markers
        lower_words = [w for w in words if w.islower()]
        formal = 1.0 - (len([w for w in lower_words if len(w) <= 2]) / max(1, len(words)))
        self.formality_level = (self.formality_level * n + formal) / new_n
        self.sample_count = new_n
        # cap vocab dict size
        if len(self.vocab_freq) > 800:
            top = dict(Counter(self.vocab_freq).most_common(500))
            self.vocab_freq = top

    def hints(self) -> str:
        bits = []
        if self.avg_message_length:
            if self.avg_message_length < 30: bits.append("брат пишет коротко — отвечай коротко")
            elif self.avg_message_length > 200: bits.append("брат пишет развёрнуто — можно длиннее")
        if self.uses_emoji: bits.append("брат использует эмодзи — допустимо умеренно")
        else: bits.append("брат не использует эмодзи — не используй")
        if self.formality_level < 0.4: bits.append("стиль брата — неформальный, в строчную")
        return "; ".join(bits) or "стиль ещё формируется"

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> "LinguisticProfile":
        if path.exists():
            try:
                return cls(**json.loads(path.read_text()))
            except Exception:
                pass
        return cls()
