from datetime import datetime
from typing import List

from pydantic import BaseModel
from pydantic import ConfigDict

from schemas.history import HistoryOut
from schemas.user import UserShortOut

class HistoryViewCreate(BaseModel):
    history_id: int

class HistoryViewsBulkCreate(BaseModel):
    history_ids: List[int]

class HistoryViewOut(BaseModel):
    id: int
    user_id: int
    history_id: int
    viewed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class HistoryViewWithHistoryOut(BaseModel):
    id: int
    user_id: int
    history: HistoryOut
    viewed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class HistoryViewWithUserOut(BaseModel):
    id: int
    history_id: int
    user: UserShortOut
    viewed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class HistoryViewsResponse(BaseModel):
    history_ids: List[int]
    histories: List[HistoryOut]
    total: int
    skip: int
    limit: int
