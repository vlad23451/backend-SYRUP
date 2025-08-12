"""Зависимости аутентификации.

Содержит вспомогательные функции для получения текущего пользователя по JWT
из cookie и проверки refresh-токена. Все ошибки переводятся в доменные
исключения для единообразной обработки middleware/декоратором.
"""
from api.auth_config import JWT_ACCESS_COOKIE_NAME, JWT_REFRESH_COOKIE_NAME
from core.jwt import decode_token
from core.logger import app_logger
from database.managers.user_manager import UserManager
from database.models.user import User
from exceptions.base import PermissionError, ValidationError
from exceptions.users import UserNotFoundError
from fastapi import Request
from jose import JWTError

user_manager = UserManager()

async def get_current_user(request: Request) -> User:
    token = request.cookies.get(JWT_ACCESS_COOKIE_NAME)
    if not token:
        app_logger.error("Отсутствует access токен")
        raise PermissionError("Отсутствует access токен")
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if sub is None:
            app_logger.error(f"Неверный токен sub: {sub} token: {token}")
            raise ValidationError("Неверный токен")
        user_id = int(sub)
    except (JWTError, ValueError):
        app_logger.error(f"Неверный токен: {token}")
        raise ValidationError("Неверный токен")
    try:
        user = await user_manager.get_obj_by_id(id=user_id)
    except UserNotFoundError as e:
        app_logger.error(f"Пользователь {user_id} не найден")
        raise UserNotFoundError()
    return user

async def validate_refresh_token(request: Request) -> int:
    refresh_token = request.cookies.get(JWT_REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise PermissionError("Отсутствует refresh токен")
    try:
        payload = decode_token(refresh_token)
        sub = payload.get("sub")
        if sub is None:
            raise ValidationError(f"Неверный токен sub: {sub} refresh_token: {refresh_token}")
        user_id = int(sub)
    except (JWTError, ValueError):
        raise ValidationError(f"Неверный токен refresh_token: {refresh_token}")

    try:
        await user_manager.get_obj_by_id(user_id)
    except UserNotFoundError:
        raise UserNotFoundError()

    return user_id
