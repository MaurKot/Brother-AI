"""Custom API endpoint — STUB for exposing Kai externally.

══════════════════════════════════════════════════════════════════════════════
КАК СНЯТЬ ЗАГЛУШКУ И ОТКРЫТЬ СВОЙ ВНЕШНИЙ API
══════════════════════════════════════════════════════════════════════════════

Сейчас этот модуль — заглушка. Здесь можно завести собственное HTTP API,
через которое посторонние системы (твой сайт, мобильное приложение, другие боты)
смогут общаться с Каем.

ВАЖНО: по умолчанию Кай говорит ТОЛЬКО с одним человеком (брат, по
BROTHER_TELEGRAM_ID). Открытие внешнего API — отдельное архитектурное решение.
Подумай, кому ты хочешь дать доступ и как его авторизовать.

──────────────────────────────────────────────────────────────────────────────
ШАГИ ДЛЯ АКТИВАЦИИ
──────────────────────────────────────────────────────────────────────────────

1. Заведи переменную окружения с секретом:
      KAI_API_TOKEN = "<длинная случайная строка>"

   Любой запрос должен передавать заголовок:
      Authorization: Bearer <тот же KAI_API_TOKEN>

2. Реализуй обработчики ниже (`_handle_chat`, `_handle_state`).
   Они уже получают ссылку на главный объект Kai, поэтому могут вызывать
   любые его методы — например `kai._on_brother_message(text)` или
   читать `kai.neuro`, `kai.mood`, `kai.memory.recent()`.

3. В файле kai/kai.py добавь после `self.web = WebMiniapp(...)`:
       from .limbs.custom_api import CustomAPI
       self.custom_api = CustomAPI(self)
   и в `run()`:
       await self.custom_api.start()
   и в shutdown_mgr:
       self.shutdown_mgr.register(self.custom_api.stop)

4. Открой нужный порт. По умолчанию 5001 — можно поменять через
   KAI_API_PORT. На Amvera добавь второй containerPort или используй
   reverse-proxy на уже открытый 5000.

5. Документируй у себя:
       POST /v1/chat
         Headers: Authorization: Bearer <token>
         Body:    {"text": "..."}
         Returns: {"reply": "..."}

       GET /v1/state
         Headers: Authorization: Bearer <token>
         Returns: {neurochem, mood, ...}

──────────────────────────────────────────────────────────────────────────────
ОПАСНЫЕ СЦЕНАРИИ (НЕ ДЕЛАЙ)
──────────────────────────────────────────────────────────────────────────────
- НЕ открывай API без токена. Любой в интернете сможет заставить Кая
  тратить твой LLM-бюджет.
- НЕ давай через API возможность изменять `neuro`, `identity`, `principles`
  напрямую — это его суверенитет.
- НЕ возвращай в ответах долгую память целиком — это его личное.
══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations
import os
from typing import Optional

from aiohttp import web

from ..logger import logger


class CustomAPI:
    """STUB — реализуй обработчики под свои нужды."""

    def __init__(self, kai, port: Optional[int] = None) -> None:
        self.kai = kai
        self.port = port or int(os.environ.get("KAI_API_PORT", "5001"))
        self.token = os.environ.get("KAI_API_TOKEN", "").strip()
        self.app = web.Application()
        self.app.router.add_post("/v1/chat", self._handle_chat)
        self.app.router.add_get("/v1/state", self._handle_state)
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

    def _check_auth(self, request: web.Request) -> bool:
        if not self.token:
            return False
        header = request.headers.get("Authorization", "")
        return header == f"Bearer {self.token}"

    async def _handle_chat(self, request: web.Request) -> web.Response:
        """ЗАГЛУШКА. Раскомментируй и допили под свои нужды."""
        if not self._check_auth(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        # body = await request.json()
        # text = body.get("text", "")
        # if not text:
        #     return web.json_response({"error": "empty"}, status=400)
        # reply = await self.kai._on_brother_message(text)
        # return web.json_response({"reply": reply})
        return web.json_response({"error": "not implemented yet"}, status=501)

    async def _handle_state(self, request: web.Request) -> web.Response:
        """ЗАГЛУШКА. Верни что считаешь нужным."""
        if not self._check_auth(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        # return web.json_response({
        #     "mood": self.kai.mood.label,
        #     "neuro": {
        #         "dopamine": self.kai.neuro.dopamine,
        #         "serotonin": self.kai.neuro.serotonin,
        #         ...
        #     },
        # })
        return web.json_response({"error": "not implemented yet"}, status=501)

    async def start(self) -> None:
        if not self.token:
            logger.info(
                "custom_api",
                "KAI_API_TOKEN не задан — внешний API НЕ запускается. "
                "См. инструкции в kai/limbs/custom_api.py.",
            )
            return
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, "0.0.0.0", self.port)
        await self._site.start()
        logger.info("custom_api", f"external API listening on 0.0.0.0:{self.port}")

    async def stop(self) -> None:
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
