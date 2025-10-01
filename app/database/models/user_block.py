from datetime import datetime
from datetime import timezone

from database.config import Base

from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User


class UserBlock(Base):
    """Модель для блокировки пользователей.
    
    Обеспечивает возможность блокировать пользователей с указанием причины.
    Один пользователь может заблокировать другого только один раз.
    """
    __tablename__ = 'user_blocks'

    id: Mapped[int] = mapped_column(primary_key=True)
    
    blocker_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'),
        nullable=False,
        index=True,
    )
    
    blocked_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'),
        nullable=False,
        index=True,
    )
    
    reason: Mapped[str | None] = mapped_column(
        nullable=True,
        default=None
    )
    
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Связи
    blocker: Mapped["User"] = relationship(
        'User', 
        foreign_keys=[blocker_id],
        back_populates='blocked_users'
    )
    blocked: Mapped["User"] = relationship(
        'User', 
        foreign_keys=[blocked_id],
        back_populates='blocked_by_users'
    )

    # Уникальное ограничение: один пользователь может заблокировать другого только один раз
    __table_args__ = (
        UniqueConstraint('blocker_id', 'blocked_id', name='unique_user_block'),
    )
