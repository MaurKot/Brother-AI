"""Integration of multi-user approval system with Telegram bot."""
from __future__ import annotations
from typing import Callable, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ..logger import logger
from .multi_user_manager import (
    ApprovalRequest,
    MultiUserManager,
    RequestType,
)


class TelegramApprovalHelper:
    """Helper для интеграции системы одобрения в Telegram."""

    def __init__(self, manager: MultiUserManager) -> None:
        self.manager = manager

    async def notify_admins_of_request(
        self,
        app,
        request: ApprovalRequest,
        user_name: Optional[str] = None,
    ) -> None:
        """Уведомить всех админов о новом запросе."""
        # Получить всех админов
        admins = [
            u for u in self.manager.users.values()
            if u.role.value in ["primary", "admin"] and u.is_active
        ]

        message_text = self._format_approval_message(request, user_name)

        for admin in admins:
            try:
                kb = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "✓ Одобрить",
                            callback_data=f"approve:{request.request_id}",
                        ),
                        InlineKeyboardButton(
                            "✗ Отклонить",
                            callback_data=f"reject:{request.request_id}",
                        ),
                    ]
                ])
                await app.bot.send_message(
                    chat_id=admin.user_id,
                    text=message_text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "telegram_approval",
                    f"failed to notify admin {admin.user_id}: {e!r}",
                )

    def _format_approval_message(
        self,
        request: ApprovalRequest,
        user_name: Optional[str],
    ) -> str:
        """Форматировать сообщение для админов."""
        user_info = user_name or f"пользователь {request.user_id}"
        return (
            f"<b>Запрос на одобрение</b>\n\n"
            f"<b>От:</b> {user_info}\n"
            f"<b>Тип:</b> {self._type_name(request.request_type)}\n"
            f"<b>Содержание:</b>\n"
            f"<code>{request.content[:200]}</code>\n\n"
            f"ID: <code>{request.request_id}</code>"
        )

    @staticmethod
    def _type_name(rt: RequestType) -> str:
        """Красивое имя типа запроса."""
        names = {
            RequestType.MESSAGE: "Сообщение",
            RequestType.API_CALL: "Вызов API",
            RequestType.SYSTEM_ACCESS: "Доступ к системе",
            RequestType.FILE_WRITE: "Запись файла",
            RequestType.EXTERNAL: "Внешний запрос",
        }
        return names.get(rt, str(rt))

    async def handle_approval_callback(
        self,
        update: Update,
        ctx: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Обработчик кнопок одобрения/отклонения."""
        query = update.callback_query
        await query.answer()

        if not query.data:
            return

        parts = query.data.split(":", 1)
        if len(parts) != 2:
            return

        action, request_id = parts
        admin_id = update.effective_user.id

        if action == "approve":
            success = self.manager.approve_request(request_id, admin_id)
            reply = "✓ Запрос одобрен" if success else "✗ Не удалось одобрить"
        elif action == "reject":
            success = self.manager.reject_request(request_id, admin_id)
            reply = "✗ Запрос отклонен" if success else "✗ Не удалось отклонить"
        else:
            return

        await query.edit_message_text(reply)

    async def get_pending_status(self, admin_id: int) -> str:
        """Получить статус pending запросов для админа."""
        pending = self.manager.get_pending_for_admin(admin_id)
        if not pending:
            return "✓ Все запросы обработаны"

        lines = [f"⏳ {len(pending)} запросов на одобрение:\n"]
        for req in pending[:5]:  # Первые 5
            user = self.manager.get_user(req.user_id)
            user_name = user.name if user else f"пользователь {req.user_id}"
            lines.append(
                f"  • {self._type_name(req.request_type)} от {user_name} "
                f"(ID: {req.request_id})"
            )
        if len(pending) > 5:
            lines.append(f"  ... и ещё {len(pending) - 5}")
        return "\n".join(lines)
