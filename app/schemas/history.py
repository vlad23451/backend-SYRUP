from datetime import datetime
from typing import List

from pydantic import BaseModel
from pydantic import ConfigDict

from schemas.author import AuthorOut
from schemas.user import UserShortOutWithFollowStatus
from schemas.file import FileOut

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
    attached_files: List[FileOut] = []
    author: AuthorOut | None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model_with_counts(
        cls,
        history_obj,
        likes: int,
        dislikes: int,
        comments: int = 0,
        liked_users: List[UserShortOutWithFollowStatus] | None = None,
        disliked_users: List[UserShortOutWithFollowStatus] | None = None,
        attached_files: List[FileOut] | None = None,
    ) -> "HistoryOut":
        base = cls.model_validate(history_obj)
        return base.model_copy(update={
            "likes": int(likes or 0),
            "dislikes": int(dislikes or 0),
            "comments": int(comments or 0),
            "liked_users": liked_users or [],
            "disliked_users": disliked_users or [],
            "attached_files": attached_files or [],
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
    attached_files: List[FileOut] = []
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model_with_counts(
        cls,
        history_obj,
        likes: int,
        dislikes: int,
        comments: int = 0,
        liked_users: List[UserShortOutWithFollowStatus] | None = None,
        disliked_users: List[UserShortOutWithFollowStatus] | None = None,
        attached_files: List[FileOut] | None = None,
    ) -> "HistoryOutShort":
        base = cls.model_validate(history_obj)
        return base.model_copy(update={
            "likes": int(likes or 0),
            "dislikes": int(dislikes or 0),
            "comments": int(comments or 0),
            "liked_users": liked_users or [],
            "disliked_users": disliked_users or [],
            "attached_files": attached_files or [],
        })

class HistoryUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
