from pydantic import BaseModel

class FollowerBase(BaseModel):
    target_id: int

class FollowerCreate(FollowerBase):
    pass
