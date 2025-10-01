from datetime import datetime
from enum import Enum
from typing import Any
from typing import Dict
from typing import List

from pydantic import BaseModel
from pydantic import Field
from pydantic import ConfigDict

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"

class MessageOut(BaseModel):
    id: int
    sender_id: int
    chat_id: int
    text: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime
    is_read: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    from_me: bool
    edited_at: datetime | None = None
    is_deleted: bool = False
    is_pinned: bool = False
    attached_files: List[int] = Field(default_factory=list, description="Список ID прикрепленных файлов")

    model_config = ConfigDict(from_attributes=True, exclude={'avatar_key'})

class MessageCreate(BaseModel):
    text: str
    chat_id: int
    message_type: MessageType = MessageType.TEXT
    metadata: Dict[str, Any] | None = None
    attached_files: List[int] = Field(default_factory=list, description="Список ID прикрепленных файлов")

class MessageUpdate(BaseModel):
    text: str | None = None
    is_read: bool | None = None
    metadata: Dict[str, Any] | None = None

class ChatHistoryResponse(BaseModel):
    """Ответ с историей чата и аватарами участников"""
    companion_avatar_url: str | None = None
    messages: list[MessageOut]

class MessageSearchRequest(BaseModel):
    """Запрос поиска по сообщениям"""
    query: str = Field(..., min_length=1, max_length=100, description="Поисковый запрос")
    chat_id: int | None = Field(None, description="ID чата для поиска (если не указан, поиск по всем чатам пользователя)")
    message_type: MessageType | None = Field(None, description="Тип сообщения для фильтрации")
    date_from: datetime | None = Field(None, description="Начальная дата для поиска")
    date_to: datetime | None = Field(None, description="Конечная дата для поиска")
    limit: int = Field(50, ge=1, le=200, description="Максимальное количество результатов")
    offset: int = Field(0, ge=0, description="Смещение для пагинации")

class MessageSearchResult(BaseModel):
    """Результат поиска сообщения"""
    message: MessageOut
    chat_title: str | None = Field(None, description="Название чата")
    companion_login: str | None = Field(None, description="Логин собеседника (для приватных чатов)")
    companion_avatar_url: str | None = Field(None, description="URL аватара собеседника")
    context_before: str | None = Field(None, description="Контекст до найденного сообщения")
    context_after: str | None = Field(None, description="Контекст после найденного сообщения")

class MessageSearchResponse(BaseModel):
    """Ответ поиска по сообщениям"""
    results: list[MessageSearchResult]
    total_count: int = Field(..., description="Общее количество найденных сообщений")
    has_more: bool = Field(..., description="Есть ли еще результаты")
    query: str = Field(..., description="Поисковый запрос")

