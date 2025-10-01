from typing import TYPE_CHECKING

from datetime import datetime
from datetime import timezone

from enum import Enum as EnumType

from database.config import Base
from sqlalchemy import ForeignKey
from sqlalchemy import JSON
from sqlalchemy import Enum
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .user import User
    from .chat import Chat
    from .private_media_file import PrivateMediaFile

class MessageType(EnumType):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"

class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(primary_key=True)

    sender_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'), nullable=False, index=True)

    text: Mapped[str | None]
    message_type: Mapped[str] = mapped_column(
        Enum(MessageType, values_callable=lambda x: [e.value for e in MessageType]),
        default=MessageType.TEXT.value,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)

    message_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # Поля для операций редактирования и удаления
    edited_at: Mapped[datetime | None]
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(default=False, nullable=False)

    sender: Mapped["User"] = relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    chat: Mapped["Chat"] = relationship('Chat', back_populates='messages')
    
    private_media_files: Mapped[list["PrivateMediaFile"]] = relationship(
        'PrivateMediaFile', back_populates='message', cascade='all, delete-orphan'
    )
