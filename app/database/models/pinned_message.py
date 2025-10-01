from typing import TYPE_CHECKING
from datetime import datetime
from datetime import timezone

from database.config import Base
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .user import User
    from .message import Message
    from .chat import Chat

class PinnedMessage(Base):
    __tablename__ = 'pinned_messages'

    id: Mapped[int] = mapped_column(primary_key=True)
    
    message_id: Mapped[int] = mapped_column(ForeignKey('messages.id'), nullable=False, index=True)
    
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'), nullable=False, index=True)
    
    pinned_by_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    
    pinned_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), 
        nullable=False, 
        index=True
    )

    message: Mapped["Message"] = relationship('Message', foreign_keys=[message_id], backref='pinned_message')
    chat: Mapped["Chat"] = relationship('Chat', foreign_keys=[chat_id], backref='pinned_messages')
    pinned_by_user: Mapped["User"] = relationship('User', foreign_keys=[pinned_by_user_id], backref='pinned_messages')

    __table_args__ = (
        UniqueConstraint('message_id', 'chat_id', name='uq_pinned_message_chat'),
        {'extend_existing': True}
    )
