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
    from .history import History

class HistoryLike(Base):
    __tablename__ = 'history_likes' 

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
            
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    
    history_id: Mapped[int] = mapped_column(
        ForeignKey('histories.id', ondelete='CASCADE'),
        nullable=False
    )
    
    user: Mapped["User"] = relationship('User', back_populates='history_likes')
    history: Mapped["History"] = relationship('History', back_populates='history_likes')

    __table_args__ = (
        UniqueConstraint('user_id', 'history_id', name='uix_user_history_like'),
    )


class HistoryDislike(Base):
    __tablename__ = 'history_dislikes'

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )

    history_id: Mapped[int] = mapped_column(
        ForeignKey('histories.id', ondelete='CASCADE'),
        nullable=False
    )

    user: Mapped["User"] = relationship('User', back_populates='history_dislikes')
    history: Mapped["History"] = relationship('History', back_populates='history_dislikes')

    __table_args__ = (
        UniqueConstraint('user_id', 'history_id', name='uix_user_history_dislike'),
    )
