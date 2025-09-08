"""Роуты подписок.

Архитектурные заметки:
- Создание/удаление подписок делегировано менеджерам (`FollowersManager`,
  `FriendsManager`) и сервисам (проверка follow-статуса), роутер остаётся тонким.
- В выборках используется кэш (внутри менеджеров) и параллельная загрузка
  связанных данных (`asyncio.gather`).
"""
import asyncio

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from api.dependencies.auth import get_current_user
from api.dependencies.pagination import get_large_pagination

from api.docs.followers import follow_description
from api.docs.followers import follower_create_responses
from api.docs.followers import follower_delete_responses
from api.docs.followers import follower_get_responses
from api.docs.followers import get_followers_description
from api.docs.followers import get_following_description
from api.docs.followers import unfollow_description

from core.logger import app_logger

from database.managers.followers_manager import FollowersManager
from database.managers.friends_manager import FriendsManager
from database.managers.user_manager import UserManager

from database.models.user import User

from schemas.followers import FollowerCreate
from schemas.response import FollowResponse
from schemas.user import UserShortOutWithFollowStatus

from services.error_handler_service import handle_api_errors
from services.user_info_service import build_user_info_many
from services.friend_service import check_follow_status

followers_router = APIRouter(prefix="/followers", tags=["Подписки"])

followers_manager = FollowersManager()
user_manager = UserManager()
friend_manager = FriendsManager()

@followers_router.post("/",
                       summary="Подписаться на пользователя",
                       status_code=status.HTTP_201_CREATED,
                       responses=follower_create_responses,
                       description=follow_description)
@handle_api_errors("Ошибка при подписке")
async def follow(target: FollowerCreate,
                 user: User = Depends(get_current_user)) -> FollowResponse:
    await followers_manager.follow(target_id=target.target_id, follower_id=user.id)
    await friend_manager.add_friend(user_id=user.id, friend_id=target.target_id)
    app_logger.info_event("user_followed", user_id=user.id, target_id=target.target_id)
    status = await check_follow_status(user_id=user.id, follower_id=target.target_id)
    return FollowResponse(follow_status=status)

@followers_router.delete("/",
                         summary="Отписаться от пользователя",
                         status_code=status.HTTP_200_OK,
                         responses=follower_delete_responses,
                         description=unfollow_description)
@handle_api_errors("Ошибка при отписке")
async def unfollow(follower: FollowerCreate,
                   user: User = Depends(get_current_user)) -> FollowResponse:
    await followers_manager.unfollow(follower.target_id, user.id)
    friends = await friend_manager.get_friends(user.id)
    is_friend = any(
        (f.user_id == min(user.id, follower.target_id) and f.friend_id == max(user.id, follower.target_id))
        for f in friends
    )
    if is_friend:
        await friend_manager.remove_friend(user.id, follower.target_id)
    app_logger.info_event("user_unfollowed", user_id=user.id, target_id=follower.target_id)
    status = await check_follow_status(user_id=user.id, follower_id=follower.target_id)
    return FollowResponse(follow_status=status)

@followers_router.get("/{id}",
                      summary="Получить список подписчиков по ID",
                      status_code=status.HTTP_200_OK,
                      responses=follower_get_responses,
                      description=get_followers_description)
@handle_api_errors("Ошибка при получении подписчиков")
async def get_followers(id: int,
                        user: User = Depends(get_current_user),
                        pagination: tuple[int, int] = Depends(get_large_pagination)) -> list[UserShortOutWithFollowStatus]:
    skip, limit = pagination
    followers = await followers_manager.get_followers(id, skip=skip, limit=limit)
    users = await asyncio.gather(*[user_manager.get_obj_by_id(f.follower_id) for f in followers])
    info_map = await build_user_info_many(me_user_id=user.id, users=users)
    result = [info_map[u.id] for u in users]
    app_logger.info_event("followers_fetched", target_user_id=id, count=len(result), skip=skip, limit=limit, user_id=user.id)
    return result

@followers_router.get("/following/{id}",
                      summary="Получить список подписок по ID пользователя",
                      status_code=status.HTTP_200_OK,
                      responses=follower_get_responses,
                      description=get_following_description)
@handle_api_errors("Ошибка при получении подписок")
async def get_following(id: int,
                        user: User = Depends(get_current_user),
                        pagination: tuple[int, int] = Depends(get_large_pagination)) -> list[UserShortOutWithFollowStatus]:
    skip, limit = pagination
    following = await followers_manager.get_following(id, skip=skip, limit=limit)
    users = await asyncio.gather(*[user_manager.get_obj_by_id(f.user_id) for f in following])
    info_map = await build_user_info_many(me_user_id=user.id, users=users)
    result = [info_map[u.id] for u in users]
    app_logger.info_event("following_fetched", target_user_id=id, count=len(result), skip=skip, limit=limit, user_id=user.id)
    return result
    