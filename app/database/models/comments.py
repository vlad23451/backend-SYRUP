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
    from .history import History
    from .comment_like import CommentLike, CommentDislike

class CommentType(EnumType):
    TEXT = 'text'
    IMAGE = 'image'
    FILE = 'file'
    SYSTEM = 'system'

class Comment(Base):
    __tablename__ = 'comments'

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=lambda: datetime.now(timezone.utc))
    comment_type: Mapped[str] = mapped_column(
        Enum(CommentType, values_callable=lambda x: [e.value for e in CommentType]),
        default=CommentType.TEXT.value,
        nullable=False,
    )
    comment_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    ) 
    
    history_id: Mapped[int] = mapped_column(
        ForeignKey('histories.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    user: Mapped["User"] = relationship('User', back_populates='comments')
    history: Mapped["History"] = relationship('History', back_populates='comments_rel')

    comment_likes: Mapped[list["CommentLike"]] = relationship(
        back_populates='comment',
        cascade='all, delete'
    )
    comment_dislikes: Mapped[list["CommentDislike"]] = relationship(
        back_populates='comment',
        cascade='all, delete'
    )
