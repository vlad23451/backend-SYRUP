from datetime import datetime
from enum import Enum
from typing import Any
from typing import Dict

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

    model_config = ConfigDict(from_attributes=True, exclude={'avatar_key'})

class MessageCreate(BaseModel):
    text: str
    chat_id: int
    message_type: MessageType = MessageType.TEXT
    metadata: Dict[str, Any] | None = None

class MessageUpdate(BaseModel):
    text: str | None = None
    is_read: bool | None = None
    metadata: Dict[str, Any] | None = None

class ChatHistoryResponse(BaseModel):
    """Ответ с историей чата и аватарами участников"""
    companion_avatar_url: str | None = None
    messages: list[MessageOut]

