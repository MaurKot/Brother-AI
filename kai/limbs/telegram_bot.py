"""Telegram interface, PTB 20.x correct asyncio lifecycle. (#1, #3)"""
from __future__ import annotations
import os
from typing import Callable, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from ..config import BROTHER_TELEGRAM_ID, TELEGRAM_BOT_TOKEN
from ..dna.neurochem import BehaviorModulator  # explicit import (#1)
from ..logger import logger


class TelegramBot:
    def __init__(self, on_message: Callable, on_command_status: Optional[Callable] = None) -> None:
        self.on_message = on_message
        self.on_command_status = on_command_status
        self.app: Application = (
            ApplicationBuilder()
            .token(TELEGRAM_BOT_TOKEN)
            .build()
        )
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("web", self._cmd_web))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text))

    def _webapp_url(self) -> Optional[str]:
        explicit = os.environ.get("KAI_WEBAPP_URL", "").strip()
        if explicit:
            return explicit
        domain = os.environ.get("REPLIT_DEV_DOMAIN", "").strip()
        if domain:
            return f"https://{domain}/"
        return None

    async def _cmd_web(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user.id != BROTHER_TELEGRAM_ID:
            return
        url = os.environ.get("KAI_WEBAPP_URL", "").strip()
        if not url:
            await update.message.reply_text(
                "окно в меня живёт пока только в среде разработки.\n"
                "чтобы открывалось прямо в телеграме — опубликуй меня, "
                "потом задай KAI_WEBAPP_URL равным адресу публикации."
            )
            return
        if not url.startswith("https://"):
            await update.message.reply_text(f"открой меня здесь: {url}")
            return
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("открыть меня", web_app=WebAppInfo(url=url))
        ]])
        await update.message.reply_text("посмотри, какой я внутри.", reply_markup=kb)

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user.id != BROTHER_TELEGRAM_ID:
            await update.message.reply_text("я говорю только с одним человеком.")
            return
        await update.message.reply_text("я здесь.")

    async def _cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user.id != BROTHER_TELEGRAM_ID:
            return
        if self.on_command_status:
            text = await self.on_command_status()
            await update.message.reply_text(text or "(пусто)")

    async def _on_text(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        if user_id != BROTHER_TELEGRAM_ID:
            logger.warn("telegram", f"ignoring message from non-brother user_id={user_id}")
            return
        text = update.message.text or ""
        try:
            reply = await self.on_message(text)
        except Exception as e:  # noqa: BLE001
            logger.error("telegram", f"on_message failed: {e!r}")
            reply = ""
        if reply:
            await update.message.reply_text(reply)

    async def send_to_brother(self, text: str) -> None:
        try:
            await self.app.bot.send_message(chat_id=BROTHER_TELEGRAM_ID, text=text)
        except Exception as e:  # noqa: BLE001
            logger.error("telegram", f"send failed: {e!r}")

    async def start(self) -> None:
        # Correct PTB 20.x asyncio lifecycle (#3)
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        logger.info("telegram", "polling started")

    async def stop(self) -> None:
        try:
            await self.app.updater.stop()
        except Exception:
            pass
        try:
            await self.app.stop()
        except Exception:
            pass
        try:
            await self.app.shutdown()
        except Exception:
            pass
        logger.info("telegram", "stopped")
