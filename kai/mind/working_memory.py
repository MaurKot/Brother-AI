"""Working memory — RAM-only short-term buffer. (#26)"""
from __future__ import annotations
from collections import deque
from datetime import datetime
from typing import Deque, Dict, List, Optional


class WorkingMemory:
    def __init__(self, capacity: int = 7) -> None:
        self.capacity = capacity
        self.conversation: Deque[Dict] = deque(maxlen=20)  # last 20 turns (user/kai)
        self.recent_thoughts: Deque[str] = deque(maxlen=5)
        self.attention_focus: str = "idle"
        self.active_context: Dict = {}

    def add_turn(self, role: str, text: str) -> None:
        self.conversation.append({
            "role": role, "text": text, "ts": datetime.utcnow().isoformat() + "Z"
        })

    def add_thought(self, text: str) -> None:
        self.recent_thoughts.append(text)

    def set_focus(self, focus: str, context: Optional[Dict] = None) -> None:
        self.attention_focus = focus
        if context is not None:
            self.active_context = context

    def conversation_text(self, last_n: int = 10) -> str:
        items = list(self.conversation)[-last_n:]
        return "\n".join(f"{x['role']}: {x['text']}" for x in items)

    def thoughts_text(self) -> str:
        return "\n".join(f"- {t}" for t in self.recent_thoughts)
