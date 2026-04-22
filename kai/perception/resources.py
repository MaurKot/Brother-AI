"""Resource sensor — Kai sees its own state. (#42)"""
from __future__ import annotations
from datetime import datetime
from typing import Dict


class ResourceSensor:
    def __init__(self, llm, memory, born_at: datetime) -> None:
        self.llm = llm
        self.memory = memory
        self.born_at = born_at
        self._error_log = []

    def record_error(self) -> None:
        self._error_log.append(datetime.utcnow())
        # trim
        if len(self._error_log) > 500:
            self._error_log = self._error_log[-500:]

    def errors_in_last(self, hours: int = 1) -> int:
        cutoff = datetime.utcnow().timestamp() - hours * 3600
        return sum(1 for t in self._error_log if t.timestamp() >= cutoff)

    def read(self) -> Dict:
        return {
            "api_budget_remaining_usd": max(0.0, self.llm.daily_budget - self.llm.spent_today),
            "api_spent_today_usd": self.llm.spent_today,
            "memory_size": self.memory.count(),
            "uptime_hours": (datetime.utcnow() - self.born_at).total_seconds() / 3600,
            "error_rate_1h": self.errors_in_last(1),
        }
