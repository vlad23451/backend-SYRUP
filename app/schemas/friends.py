from pydantic import BaseModel

class FriendBase(BaseModel):
    user_id: int
    friend_id: int

class FriendCreate(FriendBase):
    pass
