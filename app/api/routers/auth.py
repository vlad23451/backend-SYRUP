"""Роуты аутентификации.

Архитектурные заметки:
- Регистрация и логин делегированы в `services.auth_service`, чтобы роутер
  оставался тонким.
- Токены передаются через HTTP-only cookies. Для обновления access-токена
  используется `validate_refresh_token` (зависимость), извлекающая user_id из
  refresh-токена.
- Все неожиданные ошибки оборачиваются `handle_api_errors` в единый ответ.
"""
from api.auth_config import JWT_ACCESS_COOKIE_NAME

from api.dependencies.auth import get_current_user
from api.dependencies.auth import validate_refresh_token

from api.docs.auth import auth_login_responses
from api.docs.auth import auth_register_responses
from api.docs.auth import create_user_description
from api.docs.auth import login_description
from api.docs.auth import logout_description
from api.docs.auth import logout_responses
from api.docs.auth import refresh_access_token_description
from api.docs.auth import refresh_token_responses

from core.cookie import clear_auth_cookies
from core.cookie import set_auth_cookies
from core.jwt import create_access_token
from core.logger import app_logger

from database.models.user import User

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from fastapi import status
from fastapi.responses import JSONResponse

from schemas.user import UserAuth
from schemas.user import UserCreate

from database.managers.user_manager import UserManager
from services.auth_service import login_user
from services.auth_service import register_user
from services.error_handler_service import handle_api_errors

auth_router = APIRouter(prefix='/auth', tags=['Аутентификация'])

user_manager = UserManager()

@auth_router.post('/register',
                  summary='Создать пользователя',
                  status_code=status.HTTP_201_CREATED,
                  responses=auth_register_responses,
                  description=create_user_description)
@handle_api_errors("Ошибка при создании пользователя")
async def create_user(new_user: UserCreate) -> JSONResponse:
    """Создать пользователя. И выдать токены"""
    access_token, refresh_token = await register_user(new_user)
    response = JSONResponse(content={"message": "Пользователь успешно создан"})
    set_auth_cookies(response, access_token, refresh_token)
    app_logger.info(f"Пользователь {new_user.id} успешно создан")
    return response

@auth_router.post('/login',
                  summary='Войти в аккаунт',
                  status_code=status.HTTP_200_OK,
                  responses=auth_login_responses,
                  description=login_description)
@handle_api_errors("Ошибка при входе в аккаунт")
async def login(user: UserAuth) -> JSONResponse:
    """Войти в аккаунт. И выдать токены"""
    access_token, refresh_token = await login_user(user)
    user_id = await user_manager.get_user_id_by_login(user.login)   
    response = JSONResponse(
        content={
            "message": "Вы успешно вошли в аккаунт",
            "user_id": user_id,
        }
    )
    set_auth_cookies(response, access_token, refresh_token)
    app_logger.info(f"Пользователь {user.login} успешно вошел в аккаунт")
    return response

@auth_router.post('/refresh',
                  summary='Обновить access токен',
                  status_code=status.HTTP_200_OK,
                  responses=refresh_token_responses,
                  description=refresh_access_token_description)
@handle_api_errors("Ошибка при обновлении access токена")
async def refresh_access_token(response: Response,
                               user_id: int = Depends(validate_refresh_token)) -> Response:
    """Обновить access токен"""
    access_token = create_access_token({"sub": str(user_id)})
    response = JSONResponse(content={"message": "Access токен обновлен"})
    response.set_cookie(JWT_ACCESS_COOKIE_NAME, access_token)
    app_logger.info(f"Access токен обновлен для пользователя user_id={user_id}")
    return response

@auth_router.post('/logout',
                  summary='Выйти из аккаунта',
                  status_code=status.HTTP_200_OK,
                  responses=logout_responses,
                  description=logout_description)
async def logout(response: Response,
                 user: User = Depends(get_current_user)) -> Response:
    """Выйти из аккаунта и почистить за собой куки"""
    response.status_code = status.HTTP_200_OK
    response.content = {"message": "Вы успешно вышли из аккаунта"}
    clear_auth_cookies(response)
    app_logger.info(f"Пользователь {user.id} вышел из аккаунта")
    return response
