from datetime import datetime
from typing import List

from pydantic import BaseModel
from pydantic import Field
from pydantic import ConfigDict

from schemas.message import MessageOut
from schemas.user import UserShortOutWithFollowStatus

class PinnedMessageCreate(BaseModel):
    """Схема для создания закрепленного сообщения"""
    message_id: int = Field(..., description="ID сообщения для закрепления")

class PinnedMessageUpdate(BaseModel):
    """Схема для обновления закрепленного сообщения"""
    message_id: int | None = Field(None, description="ID сообщения для закрепления")

class PinnedMessageOut(BaseModel):
    """Схема для вывода закрепленного сообщения"""
    id: int
    message_id: int
    chat_id: int
    pinned_by_user_id: int
    pinned_at: datetime
    
    # Связанные объекты
    message: MessageOut | None = None
    pinned_by_user: UserShortOutWithFollowStatus | None = None
    
    model_config = ConfigDict(from_attributes=True)

class PinnedMessageWithContext(BaseModel):
    """Закрепленное сообщение с контекстом чата"""
    id: int
    message: MessageOut
    chat_title: str | None = None
    companion_login: str | None = None
    companion_avatar_url: str | None = None
    pinned_by_user: UserShortOutWithFollowStatus
    pinned_at: datetime

class PinnedMessageListResponse(BaseModel):
    """Ответ со списком закрепленных сообщений"""
    pinned_messages: List[PinnedMessageWithContext]
    total_count: int
    chat_id: int | None = None

class PinMessageRequest(BaseModel):
    """Запрос на закрепление сообщения"""
    message_id: int = Field(..., description="ID сообщения для закрепления")

class UnpinMessageRequest(BaseModel):
    """Запрос на открепление сообщения"""
    message_id: int = Field(..., description="ID сообщения для открепления")
