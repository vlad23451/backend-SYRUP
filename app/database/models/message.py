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

class MessageType(EnumType):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"

class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(primary_key=True)

    sender_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    room_id: Mapped[str] = mapped_column(nullable=False, index=True)
    
    text: Mapped[str] = mapped_column(nullable=False)
    message_type: Mapped[str] = mapped_column(
        Enum(MessageType, values_callable=lambda x: [e.value for e in MessageType]),
        default=MessageType.TEXT.value,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    message_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    sender: Mapped["User"] = relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver: Mapped["User"] = relationship('User', foreign_keys=[receiver_id], backref='received_messages')
