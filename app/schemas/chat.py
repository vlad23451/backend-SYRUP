from datetime import datetime
from typing import List

from pydantic import BaseModel
from pydantic import ConfigDict

class ChatOut(BaseModel):
    id: int
    title: str | None = None
    chat_type: str = 'private'
    participants: List[int]
    created_at: datetime
    updated_at: datetime
    chat_metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)

class ChatPreview(BaseModel):
    """Превью чата для списка чатов."""
    chat_id: int
    companion_id: int | None = None  # Для приватных чатов
    companion_login: str | None = None  # Для приватных чатов
    companion_avatar_url: str | None = None  # URL аватара собеседника
    title: str | None = None  # Для групповых чатов
    last_message: str
    last_message_time: datetime
    from_me: bool
    is_read: bool

    model_config = ConfigDict(from_attributes=True)

class ChatCreate(BaseModel):
    participants: List[int]
    chat_type: str = 'private'
    title: str | None = None
