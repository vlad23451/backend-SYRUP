from enum import Enum

from pydantic import BaseModel, field_validator


class FollowStatus(Enum):
    NOT_FOLLOWING = "not_following"
    FOLLOWED_BY_ME = "followed_by_me"
    FOLLOWING_ME = "following_me"
    MUTUAL = "mutual"
    ME = "me"

class UserBase(BaseModel):
    login: str
    about: str | None = None
    avatar_url: str | None = None

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    role: int
    friends: list[int] | None = None
    followers: list[int] | None = None
    following: list[int] | None = None

    class Config:
        from_attributes = True

class UserShortOut(BaseModel):
    id: int
    login: str
    about: str | None = None
    avatar_url: str | None = None
    
    @field_validator("about", mode="before")
    def validate_about(v):
        if v is not None and len(v) > 20:
            return v[:20] + "..."
        return v

    class Config:
        from_attributes = True

class UserShortOutWithFollowStatus(UserShortOut):
    follow_status: FollowStatus

class UserAuth(BaseModel):
    login: str
    password: str

class UpdateUser(BaseModel):
    login: str | None = None
    password: str | None = None
    about: str | None = None
    avatar_url: str | None = None

class UpdateMe(BaseModel):
    about: str | None = None
    avatar_url: str | None = None

class ProfileOutFull(BaseModel):
    user_info: UserShortOutWithFollowStatus
    friends: int = 0
    followers: int = 0
    following: int = 0
    histories: int = 0
