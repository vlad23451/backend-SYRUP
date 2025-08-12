"""Роуты пользователей.

Архитектурные заметки:
- Тонкий слой роутера: валидация входов и делегирование бизнес-логики
  менеджерам и сервисам (`UserManager`, `HistoryManager`, `FollowersManager`,
  `FriendsManager`, `user_info_service`).
- Используем кэш там, где это оправдано: профили, истории, поиск.
- Параллелим независимые операции через `asyncio.gather` (профиль / метрики).
"""
import asyncio
from typing import List

from api.dependencies.auth import get_current_user
from api.dependencies.pagination import get_large_pagination
from api.docs.user import (delete_user_description,
                           get_histories_by_id_description,
                           get_histories_description, get_me_description,
                           get_user_by_id_description, patch_me_description,
                           user_delete_responses, user_get_responses,
                           user_histories_responses, user_update_responses)
from core.cookie import clear_auth_cookies
from core.logger import app_logger
from database.managers.followers_manager import FollowersManager
from database.managers.friends_manager import FriendsManager
from database.managers.history_manager import HistoryManager
from database.managers.user_manager import UserManager
from database.models.user import User
from fastapi import APIRouter, Depends, Query, Response, status
from schemas.history import HistoryOutShort
from schemas.user import (ProfileOutFull, UpdateMe, UpdateUser, UserOut,
                          UserShortOutWithFollowStatus)
from services.cache_service import UsersSearchCacheService
from services.cache_invalidation_service import CacheInvalidationService
from services.error_handler_service import handle_api_errors
from services.user_info_service import build_user_info, build_user_info_many

user_manager = UserManager()
history_manager = HistoryManager()
follower_manager = FollowersManager()
friend_manager = FriendsManager()

user_router = APIRouter(prefix='/user', tags=['Пользователи'])

@user_router.patch('/me',
                  summary='Изменить данные о себе',
                  status_code=status.HTTP_200_OK,
                  responses=user_update_responses,
                  description=patch_me_description)
@handle_api_errors("Ошибка при обновлении данных о себе")
async def patch_me(updated_user: UpdateMe,
                   user: User = Depends(get_current_user)) -> UserOut:
    update_data = UpdateUser(**updated_user.model_dump())
    result = await user_manager.update_obj(id=user.id, updated_obj=update_data)
    await CacheInvalidationService.on_user_changed(user.id)
    app_logger.info_event("user_profile_updated", user_id=user.id)
    return UserOut.model_validate(result)

@user_router.get('/me',
                 summary='Получить данные о себе',
                 status_code=status.HTTP_200_OK,
                 responses=user_get_responses,
                 description=get_me_description)
@handle_api_errors("Ошибка при получении данных о себе")
async def get_me(user: User = Depends(get_current_user)) -> ProfileOutFull:
    profile = await user_manager.get_obj_by_id(user.id)
    profile_out = await build_user_info(me_user_id=user.id, user=profile)

    histories_task = asyncio.create_task(history_manager.get_histories_by_author_id(author_id=user.id, me_user_id=user.id))
    followers_task = asyncio.create_task(follower_manager.get_followers(user.id))
    following_task = asyncio.create_task(follower_manager.get_following(user.id))
    friends_task = asyncio.create_task(friend_manager.get_friends(user.id))
    histories_list, followers_list, following_list, friends_list = await asyncio.gather(
        histories_task, followers_task, following_task, friends_task
    )
    result = ProfileOutFull(user_info=profile_out,
                            histories=len(histories_list),
                            followers=len(followers_list),
                            following=len(following_list),
                            friends=len(friends_list))
    app_logger.info_event("user_profile_fetched", user_id=user.id)
    return result

@user_router.get('/me/histories',
                 summary="Получить свои истории",
                 status_code=status.HTTP_200_OK,
                 responses=user_histories_responses,
                 description=get_histories_description)
@handle_api_errors("Ошибка при получении своих историй")
async def get_histories(user: User = Depends(get_current_user),
                        pagination: tuple[int, int] = Depends(get_large_pagination)) -> List[HistoryOutShort]:
    skip, limit = pagination
    res = await history_manager.get_histories_by_author_id(author_id=user.id,
                                                           skip=skip,
                                                           limit=limit,
                                                           me_user_id=user.id)
    app_logger.info_event("user_histories_fetched", user_id=user.id, skip=skip, limit=limit)
    return res

@user_router.delete('/me',
                    summary='Удалить свой аккаунт',
                    status_code=status.HTTP_204_NO_CONTENT,
                    responses=user_delete_responses,
                    description=delete_user_description)
@handle_api_errors("Ошибка при удалении аккаунта")
async def delete_user(response: Response, user: User = Depends(get_current_user)) -> Response:
    await user_manager.delete_obj(id=user.id)
    clear_auth_cookies(response)
    app_logger.info_event("user_deleted", user_id=user.id)
    return response

@user_router.get('/profile/{id}',
                                summary='Получить данные о пользователе по ID',
                                status_code=status.HTTP_200_OK,
                                responses=user_get_responses,
                                description=get_user_by_id_description)
@handle_api_errors("Ошибка при получении данных о пользователе")
async def get_user_by_id(id: int,
                         user: User = Depends(get_current_user)) -> ProfileOutFull:
    profile = await user_manager.get_obj_by_id(id)
    user_out = await build_user_info(me_user_id=user.id, user=profile)
    histories = len(await history_manager.get_histories_by_author_id(author_id=profile.id, me_user_id=user.id))
    followers = len(await follower_manager.get_followers(profile.id))
    following = len(await follower_manager.get_following(profile.id))
    friends = len(await friend_manager.get_friends(profile.id))
    app_logger.info_event("user_profile_by_id_fetched", target_user_id=id, user_id=user.id)
    return ProfileOutFull(user_info=user_out,
                          histories=histories,
                          followers=followers,
                          following=following,
                          friends=friends)

@user_router.get('/profile/{id}/histories',
                 summary='Получить все истории пользователя по ID',
                 status_code=status.HTTP_200_OK,
                 responses=user_histories_responses,
                 description=get_histories_by_id_description)
@handle_api_errors("Ошибка при получении историй пользователя")
async def get_histories_by_id(id: int,
                              pagination: tuple[int, int] = Depends(get_large_pagination)) -> List[HistoryOutShort]:
    skip, limit = pagination
    result = await history_manager.get_histories_by_author_id(author_id=id, me_user_id=id, skip=skip, limit=limit)
    app_logger.info_event("user_histories_by_id_fetched", target_user_id=id, skip=skip, limit=limit)
    return result

@user_router.get('/search',
                 summary='Поиск пользователей по логину',
                 status_code=status.HTTP_200_OK)
@handle_api_errors("Ошибка при поиске пользователей")
async def search_users(q: str,
                       me: User = Depends(get_current_user),
                       pagination: tuple[int, int] = Depends(get_large_pagination)) -> list[UserShortOutWithFollowStatus]:
    skip, limit = pagination
    cached = await UsersSearchCacheService.get_search(query=q, skip=skip, limit=limit, me_user_id=me.id)
    if cached is not None:
        app_logger.info_event("users_search_cached", query=q, skip=skip, limit=limit, user_id=me.id)
        return cached
    users = await user_manager.search_users(query=q, skip=skip, limit=limit)
    info_map = await build_user_info_many(me_user_id=me.id, users=users)
    result = [info_map[u.id] for u in users]
    await UsersSearchCacheService.set_search(query=q, skip=skip, limit=limit, me_user_id=me.id, data=result)
    app_logger.info_event("users_searched", query=q, count=len(result), skip=skip, limit=limit, user_id=me.id)
    return result
