from datetime import datetime
from typing import List

from pydantic import BaseModel
from schemas.user import UserShortOutWithFollowStatus
from schemas.media import MediaFileResponse

class CommentBase(BaseModel):
    content: str
    history_id: int

class CommentCreate(CommentBase):
    comment_type: str = 'text'
    comment_metadata: dict = {}

class CommentUpdate(BaseModel):
    content: str | None

class CommentFilesUpdate(BaseModel):
    attached_file_ids: List[int]

class CommentOut(BaseModel):
    id: int 
    content: str
    created_at: datetime
    updated_at: datetime | None = None
    user_info: UserShortOutWithFollowStatus
    likes: int = 0
    dislikes: int = 0
    liked_users: List[UserShortOutWithFollowStatus] = []
    disliked_users: List[UserShortOutWithFollowStatus] = []

    comment_type: str = 'text'
    comment_metadata: dict | None = {}
    attached_files: List[MediaFileResponse] = []

    class Config:
        from_attributes = True

    @classmethod
    def from_model_with_counts(
        cls,
        comment,
        user_info,
        likes_count: int = 0,
        dislikes_count: int = 0,
        liked_users: List[UserShortOutWithFollowStatus] | None = None,
        disliked_users: List[UserShortOutWithFollowStatus] | None = None,
        attached_files: List[MediaFileResponse] | None = None,
    ):
        return cls(
            id=comment.id,
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            user_info=user_info,
            likes=likes_count,
            dislikes=dislikes_count,
            liked_users=liked_users or [],
            disliked_users=disliked_users or [],
            comment_type=comment.comment_type,
            comment_metadata=comment.comment_metadata,
            attached_files=attached_files or []
        )
