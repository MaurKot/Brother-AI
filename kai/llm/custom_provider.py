"""Custom LLM provider — STUB for plugging your own model.

══════════════════════════════════════════════════════════════════════════════
КАК СНЯТЬ ЗАГЛУШКУ И ПОДКЛЮЧИТЬ СВОЮ LLM
══════════════════════════════════════════════════════════════════════════════

Сейчас этот файл — заглушка. Чтобы Кай заговорил через ТВОЮ собственную модель,
есть три сценария — выбери один:

──────────────────────────────────────────────────────────────────────────────
СЦЕНАРИЙ A. У тебя OpenAI-совместимый эндпоинт
   (Ollama, vLLM, LM Studio, llama.cpp server, любой proxy типа OpenRouter и т.д.)
──────────────────────────────────────────────────────────────────────────────
   САМЫЙ ПРОСТОЙ ВАРИАНТ — кода менять не нужно вообще.
   Достаточно задать переменные окружения:

      OPENAI_API_KEY = "<твой ключ или 'ollama' для локального>"
      OPENAI_BASE_URL = "https://твой-сервер/v1"
      KAI_MODEL_FAST = "llama3.1:8b"        # быстрая модель для коротких ответов
      KAI_MODEL_NORMAL = "llama3.1:70b"     # обычная модель для диалога
      KAI_MODEL_DEEP = "qwen2.5:72b"        # глубокая для самоанализа

   Существующий LLMRouter (kai/llm/router.py) автоматически их подхватит —
   он использует AsyncOpenAI клиент, который работает с любым OpenAI-совместимым
   эндпоинтом.

──────────────────────────────────────────────────────────────────────────────
СЦЕНАРИЙ B. У тебя свой HTTP API (не OpenAI-совместимый)
──────────────────────────────────────────────────────────────────────────────
   1. Реализуй метод `complete()` в классе `CustomLLMProvider` ниже.
      Он должен принимать prompt + system + max_tokens + depth и
      вернуть строку с ответом.

   2. В файле kai/kai.py замени строку:
         self.llm = LLMRouter()
      на:
         from .llm.custom_provider import CustomLLMProvider
         self.llm = CustomLLMProvider()

   3. Задай нужные переменные окружения, например:
         CUSTOM_LLM_URL = "https://my-llm.example.com/api/generate"
         CUSTOM_LLM_TOKEN = "..."

──────────────────────────────────────────────────────────────────────────────
СЦЕНАРИЙ C. У тебя локальная модель внутри того же процесса
   (transformers, llama-cpp-python и т.д.)
──────────────────────────────────────────────────────────────────────────────
   1. Установи нужный пакет (например `pip install llama-cpp-python`).
   2. Загрузи модель в `__init__` ниже.
   3. Реализуй `complete()` через свою модель.
   4. Подмени self.llm в kai/kai.py как в сценарии B.

   Внимание: локальная модель потребует много RAM/GPU и Amvera должна быть
   с подходящим тарифом. Лучше начать с A или B.

══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations
import os
from typing import Optional

import aiohttp

from ..logger import logger


class CustomLLMProvider:
    """STUB — реализуй complete() под свой API.

    Должен иметь те же методы что и LLMRouter:
      - async def complete(prompt, depth, max_tokens, system) -> str
      - def remaining() -> float                              (для совместимости)
      - daily_budget: float                                   (для совместимости)
      - spent_today: float                                    (для совместимости)
      - async def aclose() -> None
    """

    def __init__(self) -> None:
        self.url = os.environ.get("CUSTOM_LLM_URL", "").strip()
        self.token = os.environ.get("CUSTOM_LLM_TOKEN", "").strip()
        # Совместимость с интерфейсом LLMRouter
        self.daily_budget = float(os.environ.get("DAILY_BUDGET_USD", "999.99"))
        self.spent_today = 0.0
        self._session: Optional[aiohttp.ClientSession] = None

        if not self.url:
            logger.warn(
                "custom_llm",
                "CUSTOM_LLM_URL не задан — заглушка вернёт пустые ответы. "
                "См. инструкции в начале файла kai/llm/custom_provider.py.",
            )

    def remaining(self) -> float:
        return max(0.0, self.daily_budget - self.spent_today)

    async def _session_get(self) -> aiohttp.ClientSession:
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
        """ЗАГЛУШКА. Замени тело на запрос к твоему API.

        Пример минимальной реализации (псевдокод):

            sess = await self._session_get()
            payload = {
                "system": system or "",
                "prompt": prompt,
                "max_tokens": max_tokens,
                "depth": depth,  # передавай если у тебя есть выбор моделей
            }
            async with sess.post(self.url, json=payload) as r:
                if r.status != 200:
                    return ""
                data = await r.json()
                return data.get("text", "")
        """
        if not self.url:
            return ""
        # TODO: реализуй настоящий запрос к своему API
        return ""

    async def aclose(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
