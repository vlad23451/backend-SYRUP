from datetime import datetime
from typing import List

from pydantic import BaseModel
from pydantic import ConfigDict

from schemas.user import UserShortOut

class UserBlockCreate(BaseModel):
    blocked_user_id: int
    reason: str | None = None

class UserBlockOut(BaseModel):
    id: int
    blocker_id: int
    blocked_id: int
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserBlockWithUsersOut(BaseModel):
    id: int
    blocker: UserShortOut
    blocked: UserShortOut
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserBlockResponse(BaseModel):
    message: str
    block: UserBlockOut | None = None

class BlockedUserOut(BaseModel):
    id: int
    blocked: UserShortOut
    reason: str | None = None
    created_at: datetime
    block_status: str  # "blocked_by_me" или "blocked_me"

    model_config = ConfigDict(from_attributes=True)

class BlockedUsersResponse(BaseModel):
    items: List[BlockedUserOut]
    total: int
