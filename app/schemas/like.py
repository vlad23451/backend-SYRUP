from datetime import datetime

from pydantic import BaseModel
from schemas.user import UserShortOutWithFollowStatus


# History Like Schemas
class HistoryLikeBase(BaseModel):
    history_id: int

class HistoryLikeCreate(HistoryLikeBase):
    pass

class HistoryLikeUpdate(BaseModel):
    pass

class HistoryLikeOut(BaseModel):
    id: int
    user_id: int
    history_id: int
    created_at: datetime
    user_info: UserShortOutWithFollowStatus

    class Config:
        from_attributes = True

# History Dislike Schemas
class HistoryDislikeBase(BaseModel):
    history_id: int

class HistoryDislikeCreate(HistoryDislikeBase):
    pass

class HistoryDislikeUpdate(BaseModel):
    pass

class HistoryDislikeOut(BaseModel):
    id: int
    user_id: int
    history_id: int
    created_at: datetime
    user_info: UserShortOutWithFollowStatus

    class Config:
        from_attributes = True

# Comment Like Schemas
class CommentLikeBase(BaseModel):
    comment_id: int

class CommentLikeCreate(CommentLikeBase):
    pass

class CommentLikeUpdate(BaseModel):
    pass

class CommentLikeOut(BaseModel):
    id: int
    user_id: int
    comment_id: int
    created_at: datetime
    user_info: UserShortOutWithFollowStatus

    class Config:
        from_attributes = True

# Comment Dislike Schemas
class CommentDislikeBase(BaseModel):
    comment_id: int

class CommentDislikeCreate(CommentDislikeBase):
    pass

class CommentDislikeUpdate(BaseModel):
    pass

class CommentDislikeOut(BaseModel):
    id: int
    user_id: int
    comment_id: int
    created_at: datetime
    user_info: UserShortOutWithFollowStatus

    class Config:
        from_attributes = True
