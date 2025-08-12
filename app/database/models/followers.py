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

class Follower(Base):
    __tablename__ = 'followers'
    __table_args__ = (
        CheckConstraint("user_id != follower_id", name="check_unique_followers"),
        Index('ix_followers_user_id_follower_id', 'user_id', 'follower_id'),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'),
        nullable=False,
        primary_key=True
    )

    follower_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'),
        nullable=False,
        primary_key=True
    )
                     
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(
        'User', foreign_keys=[user_id], back_populates='followers'
    )
    
    follower: Mapped["User"] = relationship(
        'User', foreign_keys=[follower_id], back_populates='following'
    )
