from datetime import datetime
from typing import List

from pydantic import BaseModel
from pydantic import ConfigDict

from schemas.history import HistoryOut
from schemas.user import UserShortOut


class FavoriteCreate(BaseModel):
    history_id: int


class FavoriteOut(BaseModel):
    id: int
    user_id: int
    history_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FavoriteWithHistoryOut(BaseModel):
    id: int
    user_id: int
    history: HistoryOut
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FavoriteWithUserOut(BaseModel):
    id: int
    history_id: int
    user: UserShortOut
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FavoritesResponse(BaseModel):
    history_ids: List[int]
    histories: List[HistoryOut]
    total: int
    skip: int
    limit: int
