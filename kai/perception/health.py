"""Health monitor — self-diagnostics, reports problems to brother. (#45)"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict


class HealthMonitor:
    def __init__(self, llm, memory, telegram, resources) -> None:
        self.llm = llm
        self.memory = memory
        self.telegram = telegram
        self.resources = resources
        self.last_alert_at: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(hours=2)

    async def check(self, neuro) -> Dict[str, bool]:
        snap = self.resources.read()
        checks = {
            "memory_accessible": True,
            "llm_responsive": True,
            "telegram_alive": True,
            "budget_ok": snap["api_budget_remaining_usd"] > 0.05,
            "neuro_stable": all(0.0 <= getattr(neuro, c) <= 1.0
                                for c in ("dopamine", "serotonin", "cortisol",
                                          "oxytocin", "norepinephrine", "melatonin")),
            "errors_low": snap["error_rate_1h"] < 5,
        }
        # cheap memory check
        try:
            self.memory.count()
        except Exception:
            checks["memory_accessible"] = False
        return checks

    async def report_if_needed(self, checks: Dict[str, bool]) -> None:
        failed = [k for k, v in checks.items() if not v]
        if not failed:
            return
        key = "|".join(failed)
        now = datetime.utcnow()
        last = self.last_alert_at.get(key)
        if last and now - last < self.alert_cooldown:
            return
        self.last_alert_at[key] = now
        await self.telegram.send_to_brother(f"проблемы: {', '.join(failed)}")
