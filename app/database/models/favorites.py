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

class Favorite(Base):
    __tablename__ = 'favorites'

    id: Mapped[int] = mapped_column(primary_key=True)
    
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'), 
        nullable=False,
        index=True,
    )
    
    history_id: Mapped[int] = mapped_column(
        ForeignKey('histories.id'), 
        nullable=False,
        index=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Связи
    user: Mapped["User"] = relationship('User', back_populates='favorites')
    history: Mapped["History"] = relationship('History', back_populates='favorites')

    # Уникальное ограничение: пользователь может добавить историю в избранное только один раз
    __table_args__ = (
        UniqueConstraint('user_id', 'history_id', name='unique_user_history_favorite'),
    )
