from typing import TYPE_CHECKING

from datetime import datetime
from datetime import timezone

from database.config import Base
from sqlalchemy import CheckConstraint
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .user import User

class Friend(Base):
    __tablename__ = 'friends'
    __table_args__ = (
        CheckConstraint("user_id < friend_id", name="check_unique_friends"),
        Index('ix_friends_user_id_friend_id', 'user_id', 'friend_id'),
    )
    
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    friend_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    
    user: Mapped["User"] = relationship(
        'User', foreign_keys=[user_id], back_populates='initiated_friendships'
    )
    
    friend: Mapped["User"] = relationship(
        'User', foreign_keys=[friend_id], back_populates='received_friendships'
    )
