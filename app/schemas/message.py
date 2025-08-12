from datetime import datetime
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"

class MessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    room_id: str
    text: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime
    is_read: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    from_me: bool

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    text: str
    receiver_id: int
    message_type: MessageType = MessageType.TEXT
    metadata: Dict[str, Any] | None = None


class MessageUpdate(BaseModel):
    text: str | None = None
    is_read: bool | None = None
    metadata: Dict[str, Any] | None = None

    class Config:
        from_attributes = True
