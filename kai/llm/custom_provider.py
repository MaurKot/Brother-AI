"""Custom LLM provider — реализация через Hugging Face Inference API (бесплатный).

══════════════════════════════════════════════════════════════════════════════
КАК ИСПОЛЬЗОВАТЬ
══════════════════════════════════════════════════════════════════════════════

1. Получи токен на https://huggingface.co/settings/tokens
2. Задай переменную окружения: HF_TOKEN=your_token
3. В kai/kai.py уже настроено использование CustomLLMProvider

Модели настраиваются через переменные:
- HF_MODEL_FAST: быстрая модель (по умолчанию microsoft/DialoGPT-medium)
- HF_MODEL_NORMAL: обычная (microsoft/DialoGPT-large)
- HF_MODEL_DEEP: глубокая (microsoft/DialoGPT-large)

══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations
from typing import Any, Optional

from .. import config
from ..logger import logger


class CustomLLMProvider:
    """Реализация через Hugging Face Inference API.

    Должен иметь те же методы что и LLMRouter:
      - async def complete(prompt, depth, max_tokens, system) -> str
      - def remaining() -> float
      - daily_budget: float
      - spent_today: float
      - async def aclose() -> None
    """

    def __init__(self) -> None:
        self.token = config.HF_TOKEN
        self.daily_budget = config.DAILY_BUDGET_USD
        self.spent_today = 0.0  # HF бесплатный
        self._session: Optional[Any] = None

    def remaining(self) -> float:
        """Оставшийся бюджет (для совместимости с LLMRouter)."""
        return max(0.0, self.daily_budget - self.spent_today)

    async def _session_get(self) -> Any:
        import aiohttp

        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def complete(
        self,
        prompt: str,
        depth: str = "normal",
        max_tokens: int = 200,
        system: Optional[str] = None,
    ) -> str:
        """Реализация через Hugging Face Inference API."""
        model = {
            "fast": config.HF_MODEL_FAST,
            "normal": config.HF_MODEL_NORMAL,
            "deep": config.HF_MODEL_DEEP,
        }.get(depth, config.HF_MODEL_NORMAL)

        if not self.token:
            return "HF_TOKEN not set"

        sess = await self._session_get()
        url = f"https://api-inference.huggingface.co/models/{model}"
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_length": len(prompt.split()) + max_tokens,
                "do_sample": True,
                "temperature": 0.7,
            }
        }
        try:
            async with sess.post(url, json=payload) as r:
                if r.status != 200:
                    error = await r.text()
                    logger.error("custom_llm", f"HF API error {r.status}: {error}")
                    return ""
                data = await r.json()
                if isinstance(data, list) and data:
                    generated = data[0].get("generated_text", "")
                    # Удалить исходный prompt из ответа
                    if generated.startswith(prompt):
                        return generated[len(prompt):].strip()
                    return generated.strip()
                return ""
        except Exception as e:
            logger.error("custom_llm", f"Exception: {e}")
            return ""

    async def aclose(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
