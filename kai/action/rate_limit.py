"""Rate limiter for spontaneous outreach. (#10)"""
from __future__ import annotations
from datetime import datetime
from typing import Optional


class RateLimiter:
    def __init__(self, min_interval_seconds: int) -> None:
        self.min_interval = min_interval_seconds
        self.last_at: Optional[datetime] = None

    def allow(self) -> bool:
        if self.last_at is None:
            return True
        return (datetime.utcnow() - self.last_at).total_seconds() >= self.min_interval

    def mark(self) -> None:
        self.last_at = datetime.utcnow()

    def seconds_until_allowed(self) -> int:
        if self.last_at is None:
            return 0
        elapsed = (datetime.utcnow() - self.last_at).total_seconds()
        return max(0, int(self.min_interval - elapsed))
