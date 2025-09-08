from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict

from schemas.user import UserShortOutWithFollowStatus

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

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)
