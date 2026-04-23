"""Multi-user approval system for Kai.

Позволяет нескольким людям взаимодействовать с Каем, где запросы требуют одобрения
или блокировки от других пользователей (администраторов).

Архитектура:
  - PRIMARY_USER (основной пользователь, обычно BROTHER_TELEGRAM_ID)
  - ADMINS (администраторы, могут одобрять/блокировать)
  - USERS (обычные пользователи, их запросы требуют одобрения)
  - PENDING (очередь запросов на одобрение)
"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set


class RequestType(str, Enum):
    """Типы запросов на одобрение."""
    MESSAGE = "message"           # Обычное сообщение от стороннего пользователя
    API_CALL = "api_call"         # Вызов API
    SYSTEM_ACCESS = "system_access"  # Доступ к системной информации
    FILE_WRITE = "file_write"     # Запись файла
    EXTERNAL = "external"         # Внешний запрос


class RequestStatus(str, Enum):
    """Статус запроса."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class UserRole(str, Enum):
    """Роль пользователя."""
    PRIMARY = "primary"      # Основной (полный доступ)
    ADMIN = "admin"          # Администратор (одобрение)
    USER = "user"            # Обычный пользователь (требует одобрения)
    GUEST = "guest"          # Гость (запросы требуют одобрения)


@dataclass
class User:
    """Описание пользователя."""
    user_id: int
    name: str
    role: UserRole
    added_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    last_seen: str = ""
    message_count: int = 0
    approved_count: int = 0    # Сколько одобрил запросов (для админов)
    rejected_count: int = 0    # Сколько отклонил запросов (для админов)
    is_active: bool = True

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["role"] = self.role.value
        return data

    @staticmethod
    def from_dict(data: Dict) -> User:
        data = data.copy()
        if isinstance(data.get("role"), str):
            data["role"] = UserRole(data["role"])
        return User(**data)


@dataclass
class ApprovalRequest:
    """Запрос на одобрение."""
    request_id: str
    user_id: int
    request_type: RequestType
    content: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: RequestStatus = RequestStatus.PENDING
    approved_by: List[int] = field(default_factory=list)
    rejected_by: List[int] = field(default_factory=list)
    resolve_at: str = ""
    notes: str = ""

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["request_type"] = self.request_type.value
        data["status"] = self.status.value
        return data

    @staticmethod
    def from_dict(data: Dict) -> ApprovalRequest:
        data = data.copy()
        if isinstance(data.get("request_type"), str):
            data["request_type"] = RequestType(data["request_type"])
        if isinstance(data.get("status"), str):
            data["status"] = RequestStatus(data["status"])
        return ApprovalRequest(**data)


class MultiUserManager:
    """Управление несколькими пользователями и системой одобрения."""

    def __init__(self, primary_user_id: int, state_file: Optional[Path] = None) -> None:
        self.primary_user_id = primary_user_id
        self.state_file = state_file or Path(__file__).parent / "multi_users.json"

        # users[user_id] = User
        self.users: Dict[int, User] = {}
        # pending_requests[request_id] = ApprovalRequest
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        # resolved_requests (history)
        self.resolved_requests: List[ApprovalRequest] = []

        self.load()
        self._ensure_primary()

    def _ensure_primary(self) -> None:
        """Гарантирует, что основной пользователь является ADMIN."""
        if self.primary_user_id not in self.users:
            self.add_user(self.primary_user_id, "Primary User", UserRole.PRIMARY)
        else:
            user = self.users[self.primary_user_id]
            if user.role != UserRole.PRIMARY:
                user.role = UserRole.PRIMARY
                self.save()

    def add_user(self, user_id: int, name: str, role: UserRole = UserRole.GUEST) -> User:
        """Добавить пользователя."""
        user = User(user_id=user_id, name=name, role=role)
        self.users[user_id] = user
        self.save()
        return user

    def remove_user(self, user_id: int) -> bool:
        """Удалить пользователя (не основного)."""
        if user_id == self.primary_user_id:
            return False
        if user_id in self.users:
            del self.users[user_id]
            self.save()
            return True
        return False

    def get_user(self, user_id: int) -> Optional[User]:
        """Получить пользователя."""
        return self.users.get(user_id)

    def set_user_role(self, user_id: int, role: UserRole) -> bool:
        """Изменить роль пользователя (не основного)."""
        if user_id == self.primary_user_id:
            return False  # Основной всегда PRIMARY
        if user_id in self.users:
            self.users[user_id].role = role
            self.save()
            return True
        return False

    def should_require_approval(self, user_id: int, request_type: RequestType) -> bool:
        """Требуется ли одобрение для этого запроса?"""
        user = self.get_user(user_id)
        if not user:
            return True  # Неизвестный пользователь требует одобрения

        if user.role == UserRole.PRIMARY:
            return False  # Основной не требует одобрения
        if user.role == UserRole.ADMIN:
            return False  # Админы не требуют одобрения
        if user.role == UserRole.USER:
            # USER требует одобрения для опасных операций
            return request_type in [
                RequestType.FILE_WRITE,
                RequestType.SYSTEM_ACCESS,
                RequestType.API_CALL,
            ]
        # GUEST требует одобрения для всего
        return True

    def create_request(
        self,
        user_id: int,
        request_type: RequestType,
        content: str,
    ) -> ApprovalRequest:
        """Создать запрос на одобрение."""
        import uuid
        request_id = str(uuid.uuid4())[:8]
        req = ApprovalRequest(
            request_id=request_id,
            user_id=user_id,
            request_type=request_type,
            content=content,
        )
        self.pending_requests[request_id] = req
        self.save()
        return req

    def approve_request(
        self,
        request_id: str,
        admin_user_id: int,
        notes: str = "",
    ) -> bool:
        """Одобрить запрос (может только PRIMARY или ADMIN)."""
        admin = self.get_user(admin_user_id)
        if not admin or admin.role not in [UserRole.PRIMARY, UserRole.ADMIN]:
            return False

        req = self.pending_requests.get(request_id)
        if not req or req.status != RequestStatus.PENDING:
            return False

        req.approved_by.append(admin_user_id)
        req.status = RequestStatus.APPROVED
        req.resolve_at = datetime.utcnow().isoformat() + "Z"
        req.notes = notes

        # Переместить из pending в resolved
        del self.pending_requests[request_id]
        self.resolved_requests.append(req)

        # Увеличить счётчик админа
        admin.approved_count += 1

        self.save()
        return True

    def reject_request(
        self,
        request_id: str,
        admin_user_id: int,
        reason: str = "",
    ) -> bool:
        """Отклонить запрос (может только PRIMARY или ADMIN)."""
        admin = self.get_user(admin_user_id)
        if not admin or admin.role not in [UserRole.PRIMARY, UserRole.ADMIN]:
            return False

        req = self.pending_requests.get(request_id)
        if not req or req.status != RequestStatus.PENDING:
            return False

        req.rejected_by.append(admin_user_id)
        req.status = RequestStatus.REJECTED
        req.resolve_at = datetime.utcnow().isoformat() + "Z"
        req.notes = reason

        # Переместить из pending в resolved
        del self.pending_requests[request_id]
        self.resolved_requests.append(req)

        # Увеличить счётчик админа
        admin.rejected_count += 1

        self.save()
        return True

    def get_pending_for_admin(self, admin_user_id: int) -> List[ApprovalRequest]:
        """Получить все pending запросы для админа."""
        admin = self.get_user(admin_user_id)
        if not admin or admin.role not in [UserRole.PRIMARY, UserRole.ADMIN]:
            return []
        return list(self.pending_requests.values())

    def record_message(self, user_id: int) -> None:
        """Записать сообщение от пользователя."""
        user = self.get_user(user_id)
        if user:
            user.message_count += 1
            user.last_seen = datetime.utcnow().isoformat() + "Z"
            self.save()

    def list_users(self) -> Dict[str, User]:
        """Список всех пользователей."""
        return self.users.copy()

    def get_stats(self) -> Dict:
        """Статистика по пользователям."""
        return {
            "total_users": len(self.users),
            "by_role": {
                role.value: len([u for u in self.users.values() if u.role == role])
                for role in UserRole
            },
            "pending_requests": len(self.pending_requests),
            "total_messages": sum(u.message_count for u in self.users.values()),
        }

    def save(self) -> None:
        """Сохранить состояние."""
        self.state_file.parent.mkdir(exist_ok=True)
        data = {
            "primary_user_id": self.primary_user_id,
            "users": {
                str(uid): user.to_dict() for uid, user in self.users.items()
            },
            "pending_requests": {
                req_id: req.to_dict()
                for req_id, req in self.pending_requests.items()
            },
            "resolved_requests": [req.to_dict() for req in self.resolved_requests[-100:]],  # Последние 100
        }
        self.state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load(self) -> None:
        """Загрузить состояние."""
        if not self.state_file.exists():
            return

        try:
            data = json.loads(self.state_file.read_text())
            self.users = {
                int(uid): User.from_dict(u_data)
                for uid, u_data in data.get("users", {}).items()
            }
            self.pending_requests = {
                req_id: ApprovalRequest.from_dict(r_data)
                for req_id, r_data in data.get("pending_requests", {}).items()
            }
            self.resolved_requests = [
                ApprovalRequest.from_dict(r_data)
                for r_data in data.get("resolved_requests", [])
            ]
        except Exception as e:
            from ..logger import logger
            logger.error("multi_user", f"load failed: {e!r}")
