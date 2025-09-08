from typing import TYPE_CHECKING
from datetime import datetime
from datetime import timezone

from database.config import Base
from sqlalchemy import ForeignKey
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .user import User
    from .message import Message

class Chat(Base):
    __tablename__ = 'chats'

    id: Mapped[int] = mapped_column(primary_key=True)  
    title: Mapped[str | None] = mapped_column(nullable=True) 
    chat_type: Mapped[str] = mapped_column(default='private', nullable=False)  # 'private', 'group'
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # JSON поле со списком участников [user_id1, user_id2, ...]
    participants: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    
    # Дополнительные метаданные чата
    chat_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    
    # Связи
    messages: Mapped[list["Message"]] = relationship(
        'Message', back_populates='chat', cascade='all, delete'
    )

class RoomParticipant(Base):
    __tablename__ = 'room_participants'

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    joined_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)  # Админ чата
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)  # Активный участник

    # Связи
    chat: Mapped["Chat"] = relationship('Chat', backref='participant_details')
    user: Mapped["User"] = relationship('User', backref='chat_participations')

    __table_args__ = (
        {'extend_existing': True}
    )
