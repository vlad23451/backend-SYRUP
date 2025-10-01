from typing import Tuple
from core.jwt import create_access_token 
from core.jwt import create_refresh_token
from core.logger import app_logger
from database.managers.user_manager import UserManager
from schemas.user import UserAuth
from schemas.user import UserCreate

user_manager = UserManager()

def create_tokens(user_id: str) -> Tuple[str, str]:
    access_token = create_access_token({"sub": str(user_id)})
    refresh_token = create_refresh_token({"sub": str(user_id)})
    return access_token, refresh_token

async def register_user(new_user: UserCreate) -> tuple[str, str]:
    created_user = await user_manager.create_user(new_user)
    app_logger.info_event("user_registered", user_id=created_user.id, login=new_user.login)
    return create_tokens(user_id=created_user.id)

async def login_user(user: UserAuth) -> tuple[str, str]:
    user = await user_manager.check_user_data(user)
    app_logger.info_event("user_logged_in", user_id=user.id, login=user.login)
    return create_tokens(user_id=user.id)
