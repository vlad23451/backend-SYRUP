from core.jwt import decode_token
from database.managers.user_manager import UserManager
from database.models.user import User
from exceptions.base import ValidationError
from exceptions.users import UserNotFoundError
from jose import JWTError

user_manager = UserManager()

async def get_current_user(token: str) -> User:
    if not token:
        raise PermissionError("Отсутствует access токен")
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise ValidationError("Неверный токен")
        user_id = int(sub)
    except (JWTError, ValueError):
        raise ValidationError("Неверный токен")
    try:
        user = await user_manager.get_obj_by_id(id=user_id)
    except UserNotFoundError as e:
        raise e
    return user
