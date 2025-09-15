from pydantic import BaseModel

class AuthorOut(BaseModel):
    id: int
    login: str
    avatar_url: str | None = None

    @staticmethod
    async def from_user(user, avatar_service=None) -> "AuthorOut":
        """Создает AuthorOut из объекта User с правильным avatar_url"""
        avatar_url = None
        if hasattr(user, 'avatar_key') and user.avatar_key and avatar_service:
            avatar_url = await avatar_service.get_avatar_url_or_none(user)
        
        data = {
            "id": user.id,
            "login": user.login,
            "avatar_url": avatar_url
        }
        return AuthorOut(**data)

    class Config:
        from_attributes = True
        exclude = {'avatar_key'}
