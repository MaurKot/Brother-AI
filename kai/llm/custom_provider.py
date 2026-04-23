"""Custom LLM provider via Hugging Face InferenceClient."""

from __future__ import annotations
codex/analyze-and-fix-errors-tcgfls

import asyncio

main
from typing import Any, Optional

from .. import config
from ..logger import logger


class CustomLLMProvider:
    """LLM provider compatible with Kai router interface."""

    FALLBACK_REPLY = (
        "я здесь. у меня сейчас проблема с внешней моделью. "
        "попробуй еще раз через минуту."
    )

    def __init__(self) -> None:
        self.token = config.HF_TOKEN
        self.daily_budget = config.DAILY_BUDGET_USD
codex/analyze-and-fix-errors-tcgfls
        self.spent_today = 0.0

        self.spent_today = 0.0  # HF бесплатный
        self._session: Optional[Any] = None
main

    def remaining(self) -> float:
        return max(0.0, self.daily_budget - self.spent_today)

 codex/analyze-and-fix-errors-tcgfls
    def _client(self, model: str) -> Any:
        from huggingface_hub import InferenceClient

        return InferenceClient(model=model, token=self.token, timeout=30)

    @staticmethod
    def _generate(client: Any, prompt: str, max_tokens: int) -> str:
        return client.text_generation(
            prompt,
            max_new_tokens=max_tokens,
            temperature=0.7,
            do_sample=True,
            return_full_text=False,
        )

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
main

    async def complete(
        self,
        prompt: str,
        depth: str = "normal",
        max_tokens: int = 200,
        system: Optional[str] = None,
    ) -> str:
        model = {
            "fast": config.HF_MODEL_FAST,
            "normal": config.HF_MODEL_NORMAL,
            "deep": config.HF_MODEL_DEEP,
        }.get(depth, config.HF_MODEL_NORMAL)

        if not self.token:
            return "HF_TOKEN not set"

        try:
            client = self._client(model)
            result = await asyncio.to_thread(self._generate, client, prompt, max_tokens)
            if isinstance(result, str) and result.strip():
                return result.strip()
            logger.warn("custom_llm", "HF returned empty response, using fallback")
            return self.FALLBACK_REPLY
        except Exception as e:  # noqa: BLE001
            logger.error("custom_llm", f"HF generation failed: {e}")
            return self.FALLBACK_REPLY

    async def aclose(self) -> None:
        return None
