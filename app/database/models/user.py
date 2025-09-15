from typing import TYPE_CHECKING

from database.config import Base
from database.models.followers import Follower
from database.models.friends import Friend

from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import DynamicMapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship 

if TYPE_CHECKING:
    from .history import History
    from .comments import Comment
    from .history_like import HistoryLike, HistoryDislike
    from .comment_like import CommentLike, CommentDislike
    from .media_file import MediaFile

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[int] = mapped_column(default=1, nullable=False, index=True)
    avatar_key: Mapped[str | None] = mapped_column(nullable=True)
    about: Mapped[str | None] = mapped_column(nullable=True)

    histories: Mapped[list["History"]] = relationship(
        'History', back_populates='author', cascade='all, delete'
    )
    
    comments: Mapped[list["Comment"]] = relationship(
        'Comment', back_populates='user', cascade='all, delete'
    )
    
    history_likes: Mapped[list["HistoryLike"]] = relationship(
        'HistoryLike', back_populates='user', cascade='all, delete'
    )

    history_dislikes: Mapped[list["HistoryDislike"]] = relationship(
        'HistoryDislike', back_populates='user', cascade='all, delete'
    )

    comment_likes: Mapped[list["CommentLike"]] = relationship(
        'CommentLike', back_populates='user', cascade='all, delete'
    )

    comment_dislikes: Mapped[list["CommentDislike"]] = relationship(
        'CommentDislike', back_populates='user', cascade='all, delete'
    )

    followers: DynamicMapped["Follower"] = relationship(
        'Follower', foreign_keys=[Follower.user_id], back_populates='user', lazy='dynamic'
    )
    
    following: DynamicMapped["Follower"] = relationship(
        'Follower', foreign_keys=[Follower.follower_id], back_populates='follower', lazy='dynamic'
    )

    initiated_friendships: Mapped[list["Friend"]] = relationship(
        'Friend', foreign_keys=[Friend.user_id], back_populates='user', cascade='all, delete-orphan'
    )
    
    received_friendships: Mapped[list["Friend"]] = relationship(
        'Friend', foreign_keys=[Friend.friend_id], back_populates='friend', cascade='all, delete-orphan'
    )
    
    media_files: Mapped[list["MediaFile"]] = relationship(
        'MediaFile', back_populates='user', cascade='all, delete-orphan'
    )
    