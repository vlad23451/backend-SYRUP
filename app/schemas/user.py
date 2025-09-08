from enum import Enum

from pydantic import BaseModel
from pydantic import field_validator
from pydantic import ConfigDict

from schemas.role import UserRole

class FollowStatus(Enum):
    NOT_FOLLOWING = "not_following"
    FOLLOWED_BY_ME = "followed_by_me"
    FOLLOWING_ME = "following_me"
    MUTUAL = "mutual"
    ME = "me"

class UserBase(BaseModel):
    login: str
    about: str | None = None
    avatar_key: str | None = None

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    role: int
    role_name: str | None = None
    friends: list[int] | None = None
    followers: list[int] | None = None
    following: list[int] | None = None

    def __init__(self, **data):
        super().__init__(**data)
        if hasattr(self, 'role') and not self.role_name:
            self.role_name = UserRole.get_role_name(self.role)

    model_config = ConfigDict(from_attributes=True)

class UserShortOut(BaseModel):
    id: int
    login: str
    about: str | None = None
    avatar_key: str | None = None
    
    @field_validator("about", mode="before")
    def validate_about(v):
        if v is not None and len(v) > 20:
            return v[:20] + "..."
        return v

    model_config = ConfigDict(from_attributes=True)

class UserShortOutWithFollowStatus(UserShortOut):
    follow_status: FollowStatus

class UserAuth(BaseModel):
    login: str
    password: str

class UpdateUser(BaseModel):
    login: str | None = None
    password: str | None = None
    about: str | None = None
    avatar_key: str | None = None

class UpdateMe(BaseModel):
    about: str | None = None
    avatar_key: str | None = None

class ProfileOutFull(BaseModel):
    user_info: UserShortOutWithFollowStatus
    friends: int = 0
    followers: int = 0
    following: int = 0
    histories: int = 0
