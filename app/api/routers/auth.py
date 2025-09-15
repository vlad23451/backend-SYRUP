"""Роуты аутентификации.

Архитектурные заметки:
- Регистрация и логин делегированы в `services.auth_service`, чтобы роутер
  оставался тонким.
- Токены передаются через HTTP-only cookies. Для обновления access-токена
  используется `validate_refresh_token` (зависимость), извлекающая user_id из
  refresh-токена.
- Все неожиданные ошибки оборачиваются `handle_api_errors` в единый ответ.
"""
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from fastapi import status
from fastapi.responses import JSONResponse

from api.dependencies.auth import get_current_user
from api.dependencies.auth import validate_refresh_token
from schemas.user import UserOut
from services.avatar_service import avatar_service

from api.docs.auth import auth_login_responses
from api.docs.auth import auth_register_responses
from api.docs.auth import create_user_description
from api.docs.auth import login_description
from api.docs.auth import logout_description
from api.docs.auth import logout_responses
from api.docs.auth import refresh_access_token_description
from api.docs.auth import refresh_token_responses
from api.docs.auth import get_token_responses
from api.docs.auth import get_token_description

from core.cookie import clear_auth_cookies
from core.cookie import set_auth_cookies
from core.jwt import create_access_token
from core.jwt import create_refresh_token
from core.logger import app_logger
from core.config import settings

from database.models.user import User

from schemas.user import UserAuth
from schemas.user import UserCreate
from schemas.user import UserOut
from schemas.token import TokenResponse

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
    db_user = await user_manager.get_user_by_login(new_user.login)
    user_info = UserOut.model_validate(db_user)
    
    response = JSONResponse(
        content={
            "user_info": user_info.model_dump(),
        }
    )
    set_auth_cookies(response, access_token, refresh_token)
    app_logger.info(f"Пользователь {new_user.login} успешно создан")
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
    db_user = await user_manager.get_user_by_login_with_relations(user.login)
    user_info = await UserOut.from_user_with_relations(db_user, avatar_service)
    
    response = JSONResponse(
        content={
            "user_info": user_info.model_dump(),
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
    refresh_token = create_refresh_token({"sub": str(user_id)})
    response = JSONResponse(content={"message": "Access токен обновлен"})
    set_auth_cookies(response, access_token, refresh_token)
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

@auth_router.get('/token',
                 summary='Получить access токен для WebSocket',
                 status_code=status.HTTP_200_OK,
                 responses=get_token_responses,
                 description=get_token_description)
@handle_api_errors("Ошибка при получении токена")
async def get_websocket_token(user: User = Depends(get_current_user)) -> TokenResponse:
    access_token = create_access_token({"sub": str(user.id)})

    app_logger.info(f"WebSocket токен выдан пользователю {user.id}")
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )
