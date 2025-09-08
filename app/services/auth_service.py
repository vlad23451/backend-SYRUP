from core.jwt import create_access_token 
from core.jwt import create_refresh_token
from core.logger import app_logger
from database.managers.user_manager import UserManager
from schemas.user import UserAuth
from schemas.user import UserCreate

user_manager = UserManager()

#TODO: Вынести создание токенов в отдельную фукнцию!

async def register_user(new_user: UserCreate) -> tuple[str, str]:
    created_user = await user_manager.create_user(new_user)
    access_token = create_access_token({"sub": str(created_user.id)})
    refresh_token = create_refresh_token({"sub": str(created_user.id)})
    app_logger.info_event("user_registered", user_id=created_user.id, login=new_user.login)
    return access_token, refresh_token

async def login_user(user: UserAuth) -> tuple[str, str]:
    user = await user_manager.check_user_data(user)
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    app_logger.info_event("user_logged_in", user_id=user.id, login=user.login)
    return access_token, refresh_token
