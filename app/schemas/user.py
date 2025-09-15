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
    avatar_url: str | None = None

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

    @staticmethod
    async def from_user_with_relations(user, avatar_service=None) -> "UserOut":
        """Создает UserOut из объекта User с загрузкой аватара и отношений"""
        avatar_url = None
        if hasattr(user, 'avatar_key') and user.avatar_key and avatar_service:
            avatar_url = await avatar_service.get_avatar_url_or_none(user)
        
        # Загружаем списки друзей, подписчиков и подписок
        friends = []
        followers = []
        following = []
        
        # Друзья - объединяем initiated_friendships и received_friendships
        if hasattr(user, 'initiated_friendships') and user.initiated_friendships:
            friends.extend([friend.friend_id for friend in user.initiated_friendships])
        if hasattr(user, 'received_friendships') and user.received_friendships:
            friends.extend([friendship.user_id for friendship in user.received_friendships])
        
        # Подписчики - используем предзагруженные ID
        if hasattr(user, '_followers_ids'):
            followers = user._followers_ids
        else:
            followers = []
        
        # Подписки - используем предзагруженные ID
        if hasattr(user, '_following_ids'):
            following = user._following_ids
        else:
            following = []
        
        data = {
            "id": user.id,
            "login": user.login,
            "about": user.about,
            "avatar_url": avatar_url,
            "role": user.role,
            "role_name": UserRole.get_role_name(user.role),
            "friends": friends,
            "followers": followers,
            "following": following
        }
        return UserOut(**data)

    model_config = ConfigDict(from_attributes=True, exclude={'avatar_key'})

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

    @staticmethod
    async def from_user(user, avatar_service=None) -> "UserShortOut":
        """Создает UserShortOut из объекта User с правильным avatar_url"""
        avatar_url = None
        if hasattr(user, 'avatar_key') and user.avatar_key and avatar_service:
            avatar_url = await avatar_service.get_avatar_url_or_none(user)
        
        data = {
            "id": user.id,
            "login": user.login,
            "about": user.about,
            "avatar_url": avatar_url
        }
        return UserShortOut(**data)

    model_config = ConfigDict(from_attributes=True, exclude={'avatar_key'})

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
