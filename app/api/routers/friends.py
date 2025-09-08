"""Роуты друзей.

Архитектура:
- Дружба доступна только при взаимной подписке (см. `FriendsManager`).
- Для списка друзей используется кэш на уровне менеджера и параллельная
  подгрузка профилей пользователей.
"""
import asyncio

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from api.dependencies.auth import get_current_user
from api.dependencies.pagination import get_large_pagination

from api.docs.friends import friend_get_responses
from api.docs.friends import get_friends_description

from core.logger import app_logger

from database.managers.friends_manager import FriendsManager
from database.managers.user_manager import UserManager

from database.models.user import User

from schemas.user import UserShortOutWithFollowStatus

from services.error_handler_service import handle_api_errors
from services.user_info_service import build_user_info_many

friends_router = APIRouter(prefix="/friends", tags=["Друзья"])

user_manager = UserManager()
friends_manager = FriendsManager()  

@friends_router.get("/{id}",
                    summary="Получить список друзей по ID пользователя",
                    status_code=status.HTTP_200_OK,
                    responses=friend_get_responses,
                    description=get_friends_description)
@handle_api_errors("Ошибка при получении друзей")
async def get_friends(id: int,
                      user: User = Depends(get_current_user),
                      pagination: tuple[int, int] = Depends(get_large_pagination)) -> list[UserShortOutWithFollowStatus]:
    skip, limit = pagination
    friends = await friends_manager.get_friends(id, skip=skip, limit=limit)
    friend_ids = [f.friend_id if f.user_id == id else f.user_id for f in friends]
    users = await asyncio.gather(*[user_manager.get_obj_by_id(uid) for uid in friend_ids])
    info_map = await build_user_info_many(me_user_id=user.id, users=users)
    result = [info_map[u.id] for u in users]
    app_logger.info_event("friends_fetched", target_user_id=id, count=len(result), skip=skip, limit=limit, user_id=user.id)
    return result
