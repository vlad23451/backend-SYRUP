import asyncio
from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Response
from fastapi import UploadFile
from fastapi import status

from api.dependencies.auth import get_current_user
from api.dependencies.pagination import get_large_pagination

from api.docs.avatar import avatar_get_responses
from api.docs.avatar import avatar_upload_responses
from api.docs.avatar import get_my_avatar_description
from api.docs.avatar import get_user_avatar_description
from api.docs.avatar import upload_my_avatar_description

from api.docs.user import change_password_description
from api.docs.user import change_password_responses
from api.docs.user import delete_user_description
from api.docs.user import get_histories_by_id_description
from api.docs.user import get_histories_description
from api.docs.user import get_me_description
from api.docs.user import get_user_by_id_description
from api.docs.user import patch_me_description
from api.docs.user import search_users_description
from api.docs.user import user_delete_responses
from api.docs.user import user_get_responses
from api.docs.user import user_histories_responses
from api.docs.user import user_update_responses

from core.cookie import clear_auth_cookies
from core.logger import app_logger

from database.managers.followers_manager import FollowersManager
from database.managers.friends_manager import FriendsManager
from database.managers.history_manager import HistoryManager
from database.managers.user_manager import UserManager

from database.models.user import User

from schemas.avatar import AvatarResponse
from schemas.avatar import UploadAvatarResponse

from schemas.history import HistoryOutShort

from schemas.user import ChangePassword
from schemas.user import ProfileOutFull
from schemas.user import UpdateMe
from schemas.user import UpdateUser
from schemas.user import UserOut
from schemas.user import UserShortOutWithFollowStatus

from services.avatar_service import avatar_service
from services.cache_service import UsersSearchCacheService
from services.cache_invalidation_service import CacheInvalidationService
from services.error_handler_service import handle_api_errors
from services.user_info_service import build_user_info
from services.user_info_service import build_user_info_many

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
    # Создаем UpdateUser только с полями, которые были переданы
    update_data = UpdateUser()
    if updated_user.about is not None:
        update_data.about = updated_user.about
    if updated_user.avatar_key is not None:
        update_data.avatar_key = updated_user.avatar_key
    
    # Логируем что обновляем
    app_logger.info(f"Updating user {user.id}: about={updated_user.about}, avatar_key={updated_user.avatar_key}")
    
    await user_manager.update_obj(id=user.id, updated_obj=update_data)
    await CacheInvalidationService.on_user_changed(user.id)
    app_logger.info_event("user_profile_updated", user_id=user.id)
    
    updated_user_with_relations = await user_manager.get_user_by_id_with_relations(user.id)
    from services.avatar_service import avatar_service
    
    # Логируем результат
    app_logger.info(f"Updated user avatar_key: {updated_user_with_relations.avatar_key}")
    
    return await UserOut.from_user_with_relations(updated_user_with_relations, avatar_service)

@user_router.patch('/me/password',
                  summary='Изменить пароль',
                  status_code=status.HTTP_200_OK,
                  responses=change_password_responses,
                  description=change_password_description)
@handle_api_errors("Ошибка при изменении пароля")
async def change_password(password_data: ChangePassword,
                         user: User = Depends(get_current_user)) -> dict:
    """Изменить пароль пользователя с проверкой старого пароля."""
    await user_manager.change_password(
        user_id=user.id,
        old_password=password_data.old_password,
        new_password=password_data.new_password
    )
    await CacheInvalidationService.on_user_changed(user.id)
    app_logger.info_event("user_password_changed", user_id=user.id)
    
    return {"message": "Пароль успешно изменен"}

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

@user_router.get('/me/avatar',
                 summary='Получить свой аватар',
                 status_code=status.HTTP_200_OK,
                 responses=avatar_get_responses,
                 description=get_my_avatar_description)
@handle_api_errors("Ошибка при получении своего аватара")
async def get_my_avatar(current_user: User = Depends(get_current_user)) -> AvatarResponse:
    url = await avatar_service.get_my_avatar_url(current_user)
    return AvatarResponse(url=url)

@user_router.post('/me/avatar',
                  summary='Загрузить свой аватар',
                  status_code=status.HTTP_200_OK,
                  responses=avatar_upload_responses,
                  description=upload_my_avatar_description)
@handle_api_errors("Ошибка при загрузке аватара")
async def upload_my_avatar(file: UploadFile = File(..., description="Файл аватара"),
                          current_user: User = Depends(get_current_user)) -> UploadAvatarResponse:
    avatar_key, url = await avatar_service.upload_my_avatar(file, current_user)
    return UploadAvatarResponse(avatar_key=avatar_key, url=url)

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

@user_router.get('/profile/{user_id}/avatar',
                 summary='Получить аватар пользователя',
                 status_code=status.HTTP_200_OK,
                 responses=avatar_get_responses,
                 description=get_user_avatar_description)
@handle_api_errors("Ошибка при получении аватара")
async def get_user_avatar(user_id: int, 
                         current_user: User = Depends(get_current_user)) -> AvatarResponse:
    url = await avatar_service.get_user_avatar_url(user_id)
    return AvatarResponse(url=url)

@user_router.get('/search',
                 summary='Поиск пользователей по логину',
                 status_code=status.HTTP_200_OK,
                 description=search_users_description)
@handle_api_errors("Ошибка при поиске пользователей")
async def search_users(q: str,
                       me: User = Depends(get_current_user),
                       friends: bool = False,
                       followers: bool = False,
                       following: bool = False,
                       pagination: tuple[int, int] = Depends(get_large_pagination)) -> list[UserShortOutWithFollowStatus]:
    skip, limit = pagination
    
    # Создаем уникальный ключ кэша с учетом фильтров
    cache_key = f"{q}_{skip}_{limit}_{me.id}_{friends}_{followers}_{following}"
    cached = await UsersSearchCacheService.get_search(query=cache_key, skip=skip, limit=limit, me_user_id=me.id)
    if cached is not None:
        app_logger.info_event("users_search_cached", query=q, skip=skip, limit=limit, user_id=me.id, filters=f"{friends}_{followers}_{following}")
        return cached
    
    # Получаем пользователей с учетом фильтров
    users = await user_manager.search_users_with_filters(
        query=q, 
        skip=skip, 
        limit=limit,
        me_user_id=me.id,
        friends_only=friends,
        followers_only=followers,
        following_only=following
    )
    
    info_map = await build_user_info_many(me_user_id=me.id, users=users)
    result = [info_map[u.id] for u in users]
    await UsersSearchCacheService.set_search(query=cache_key, skip=skip, limit=limit, me_user_id=me.id, data=result)
    app_logger.info_event("users_searched", query=q, count=len(result), skip=skip, limit=limit, user_id=me.id, filters=f"{friends}_{followers}_{following}")
    return result
