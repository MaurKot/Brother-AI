"""Will — decides whether/how to reach out spontaneously."""
from __future__ import annotations
from typing import Optional

from ..config import MIN_SPONTANEOUS_INTERVAL_SECONDS
from ..dna.neurochem import BehaviorModulator
from ..logger import logger
from .rate_limit import RateLimiter


class Will:
    def __init__(self, neuro, drives, brother_model, rate_limiter: Optional[RateLimiter] = None) -> None:
        self.neuro = neuro
        self.drives = drives
        self.brother_model = brother_model
        self.rate_limiter = rate_limiter or RateLimiter(MIN_SPONTANEOUS_INTERVAL_SECONDS)

    def should_reach_out(self) -> bool:
        if not self.rate_limiter.allow():
            return False
        bm = BehaviorModulator(self.neuro)
        social = bm.social_drive()
        # Less likely if brother was just here
        hours_since = self.brother_model.hours_since_last()
        if hours_since < 1.0:
            return False
        # Stronger urge after long silence
        threshold = 0.75 - min(0.3, (hours_since - 1.0) * 0.05)
        decision = social >= threshold
        if decision:
            logger.info("will", f"reach_out=True social={social:.2f} silence={hours_since:.1f}h")
        return decision

    def mark_reached_out(self) -> None:
        self.rate_limiter.mark()
