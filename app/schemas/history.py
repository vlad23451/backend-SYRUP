from datetime import datetime
from typing import List

from pydantic import BaseModel
from schemas.author import AuthorOut
from schemas.user import UserShortOutWithFollowStatus


class HistoryCreate(BaseModel):
    title: str
    description: str | None = None  

class HistoryOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    likes: int
    dislikes: int
    comments: int
    liked_users: List[UserShortOutWithFollowStatus] = []
    disliked_users: List[UserShortOutWithFollowStatus] = []
    author: AuthorOut | None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model_with_counts(
        cls,
        history_obj,
        likes: int,
        dislikes: int,
        comments: int = 0,
        liked_users: List[UserShortOutWithFollowStatus] | None = None,
        disliked_users: List[UserShortOutWithFollowStatus] | None = None,
    ) -> "HistoryOut":
        base = cls.model_validate(history_obj)
        return base.model_copy(update={
            "likes": int(likes or 0),
            "dislikes": int(dislikes or 0),
            "comments": int(comments or 0),
            "liked_users": liked_users or [],
            "disliked_users": disliked_users or [],
        })

class HistoryOutShort(BaseModel):
    id: int
    title: str
    description: str | None = None
    likes: int
    dislikes: int
    comments: int
    liked_users: List[UserShortOutWithFollowStatus] = []
    disliked_users: List[UserShortOutWithFollowStatus] = []
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model_with_counts(
        cls,
        history_obj,
        likes: int,
        dislikes: int,
        comments: int = 0,
        liked_users: List[UserShortOutWithFollowStatus] | None = None,
        disliked_users: List[UserShortOutWithFollowStatus] | None = None,
    ) -> "HistoryOutShort":
        base = cls.model_validate(history_obj)
        return base.model_copy(update={
            "likes": int(likes or 0),
            "dislikes": int(dislikes or 0),
            "comments": int(comments or 0),
            "liked_users": liked_users or [],
            "disliked_users": disliked_users or [],
        })

class HistoryUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
