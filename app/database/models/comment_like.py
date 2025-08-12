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
    from .comments import Comment

class CommentLike(Base):
    __tablename__ = 'comment_likes'

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )

    comment_id: Mapped[int] = mapped_column(
        ForeignKey('comments.id', ondelete='CASCADE'),
        nullable=False
    )

    user: Mapped["User"] = relationship('User', back_populates='comment_likes')
    comment: Mapped["Comment"] = relationship('Comment', back_populates='comment_likes')

    __table_args__ = (
        UniqueConstraint('user_id', 'comment_id', name='uix_user_comment_like'),
    )

class CommentDislike(Base):
    __tablename__ = 'comment_dislikes'

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )

    comment_id: Mapped[int] = mapped_column(
        ForeignKey('comments.id', ondelete='CASCADE'),
        nullable=False
    )

    user: Mapped["User"] = relationship('User', back_populates='comment_dislikes')
    comment: Mapped["Comment"] = relationship('Comment', back_populates='comment_dislikes')

    __table_args__ = (
        UniqueConstraint('user_id', 'comment_id', name='uix_user_comment_dislike'),
    )
