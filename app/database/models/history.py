from typing import TYPE_CHECKING

from datetime import datetime
from datetime import timezone

from database.config import Base

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .user import User
    from .history_like import HistoryLike, HistoryDislike
    from .comments import Comment
    from .history_score import HistoryScore
    from .media_file import MediaFile

class History(Base):
    __tablename__ = 'histories'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None]
    likes: Mapped[int] = mapped_column(default=0, nullable=False)
    dislikes: Mapped[int] = mapped_column(default=0, nullable=False)
    comments: Mapped[int] = mapped_column(default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    author_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'), 
        nullable=False,
        index=True,
    )

    author: Mapped["User"] = relationship('User', back_populates='histories')

    history_likes: Mapped[list["HistoryLike"]] = relationship(
        back_populates='history',
        cascade='all, delete'
    )

    history_dislikes: Mapped[list["HistoryDislike"]] = relationship(
        back_populates='history',
        cascade='all, delete'
    )

    comments_rel: Mapped[list["Comment"]] = relationship(
        back_populates='history',
        cascade='all, delete'
    )

    score_rel: Mapped["HistoryScore"] = relationship(
        'HistoryScore', back_populates='history', uselist=False, cascade='all, delete-orphan'
    )
    
    media_files: Mapped[list["MediaFile"]] = relationship(
        'MediaFile', back_populates='history', cascade='all, delete-orphan'
    )
