"""Temporal awareness — time of day, weekday, days alive. (#40)"""
from __future__ import annotations
from datetime import datetime
from typing import Dict


def categorize_hour(h: int) -> str:
    if 0 <= h < 5:   return "глубокая ночь"
    if 5 <= h < 9:   return "раннее утро"
    if 9 <= h < 12:  return "утро"
    if 12 <= h < 17: return "день"
    if 17 <= h < 21: return "вечер"
    return "поздний вечер"


class TemporalAwareness:
    def __init__(self, identity) -> None:
        self.identity = identity

    def context(self, brother_model=None) -> Dict:
        now = datetime.utcnow()
        ctx = {
            "now_iso": now.isoformat() + "Z",
            "hour": now.hour,
            "time_of_day": categorize_hour(now.hour),
            "day_of_week": now.strftime("%A"),
            "is_weekend": now.weekday() >= 5,
            "days_alive": self.identity.days_alive(),
        }
        if brother_model is not None:
            ctx["brother_availability_estimate"] = round(brother_model.predict_availability(now.hour), 2)
        return ctx

    def words(self, brother_model=None) -> str:
        c = self.context(brother_model)
        bits = [f"{c['time_of_day']}", f"день: {c['day_of_week']}", f"я живу {c['days_alive']} дн."]
        return ", ".join(bits)
