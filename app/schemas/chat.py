from datetime import datetime

from pydantic import BaseModel


class ChatOut(BaseModel):
    companion_id: int
    companion_login: str
    last_message: str
    last_message_time: datetime
    room_id: str
    from_me: bool
    is_read: bool

    class Config:
        from_attributes=True

class ChatCreate(BaseModel):
    room_id: str
