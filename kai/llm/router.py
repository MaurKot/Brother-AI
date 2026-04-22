"""LLM router — single shared client + persisted budget. (#7, #9, #13)"""
from __future__ import annotations
import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

from ..config import (
    DAILY_BUDGET_USD,
    MODEL_DEEP,
    MODEL_FAST,
    MODEL_NORMAL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    PRICING_PER_1K,
    STATE_DIR,
)
from ..logger import logger


BUDGET_PATH = STATE_DIR / "budget.json"


class LLMRouter:
    """Single AsyncOpenAI client. Keeps budget across restarts. Routes by depth."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        self.daily_budget = DAILY_BUDGET_USD
        self.spent_today = 0.0
        self.spent_date = date.today().isoformat()
        self._lock = asyncio.Lock()
        self._load_budget()

    def _load_budget(self) -> None:
        if not BUDGET_PATH.exists():
            return
        try:
            data = json.loads(BUDGET_PATH.read_text())
            if data.get("date") == date.today().isoformat():
                self.spent_today = float(data.get("spent", 0.0))
                self.spent_date = data["date"]
            else:
                self.spent_today = 0.0
                self.spent_date = date.today().isoformat()
                self._save_budget()
        except Exception as e:  # noqa: BLE001
            logger.warn("llm", f"budget load failed: {e!r}")

    def _save_budget(self) -> None:
        try:
            BUDGET_PATH.write_text(json.dumps({"date": self.spent_date, "spent": self.spent_today}))
        except Exception as e:  # noqa: BLE001
            logger.warn("llm", f"budget save failed: {e!r}")

    def _roll_day_if_needed(self) -> None:
        today = date.today().isoformat()
        if today != self.spent_date:
            self.spent_date = today
            self.spent_today = 0.0
            self._save_budget()

    def remaining(self) -> float:
        self._roll_day_if_needed()
        return max(0.0, self.daily_budget - self.spent_today)

    def _model_for(self, depth: str) -> str:
        if depth in ("deep",):
            return MODEL_DEEP
        if depth in ("fast", "free"):
            return MODEL_FAST
        return MODEL_NORMAL

    async def complete(
        self,
        prompt: str,
        depth: str = "normal",
        max_tokens: int = 400,
        system: Optional[str] = None,
    ) -> str:
        self._roll_day_if_needed()
        model = self._model_for(depth)

        # Force fast/free for low-priority calls when budget low
        if depth != "free" and self.remaining() < 0.05:
            model = MODEL_FAST
            logger.warn("llm", "budget low — forcing fast model")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=max_tokens,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("llm", f"chat.create failed model={model}: {e!r}")
            return ""

        content = ""
        try:
            content = resp.choices[0].message.content or ""
        except Exception:
            content = ""

        # Cost accounting
        try:
            usage = resp.usage
            total_tokens = (getattr(usage, "total_tokens", None)
                            or (getattr(usage, "prompt_tokens", 0) + getattr(usage, "completion_tokens", 0)))
            cost = total_tokens / 1000.0 * PRICING_PER_1K.get(model, 0.001)
        except Exception:
            cost = 0.0

        async with self._lock:
            self.spent_today += cost
            self._save_budget()

        return content

    async def aclose(self) -> None:
        try:
            await self.client.close()
        except Exception:
            pass
