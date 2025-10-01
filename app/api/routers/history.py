from typing import Sequence

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from fastapi import status

from api.dependencies.auth import get_current_user
from api.dependencies.ownership import get_history_or_error_with_moderation
from api.dependencies.pagination import get_small_pagination

from api.docs.history import create_history_description
from api.docs.history import delete_history_description
from api.docs.history import get_histories_description
from api.docs.history import get_history_description
from api.docs.history import history_create_responses
from api.docs.history import history_delete_responses
from api.docs.history import history_get_all_responses
from api.docs.history import history_get_responses
from api.docs.history import history_update_responses
from api.docs.history import update_history_description

from core.logger import app_logger

from database.managers.friends_manager import FriendsManager
from database.managers.comment_manager import CommentManager
from database.managers.history_manager import HistoryManager
from database.managers.followers_manager import FollowersManager
from database.managers.history_view_manager import HistoryViewManager
from database.models.history import History
from database.models.user import User

from exceptions.histories import HistoryNotFoundError

from schemas.comment import CommentOut
from schemas.history import HistoryCreate, HistoryOut, HistoryUpdate, HistoryFilesUpdate
from schemas.history import HistoryIdsIn

from services.cache_invalidation_service import CacheInvalidationService
from services.error_handler_service import handle_api_errors

history_router = APIRouter(prefix='/history', tags=['Истории'])

history_manager = HistoryManager()
comment_manager = CommentManager()
followers_manager = FollowersManager()
friends_manager = FriendsManager()
history_view_manager = HistoryViewManager()

async def ensure_ownership_or_moderation(id: int, user: User = Depends(get_current_user)) -> History:
    return await get_history_or_error_with_moderation(id=id, user=user)

@history_router.post('/',
                     summary='Создать историю',
                     status_code=status.HTTP_201_CREATED,
                     responses=history_create_responses,
                     description=create_history_description)
@handle_api_errors("Ошибка при создании истории")
async def create_history(new_history: HistoryCreate,
                         user: User = Depends(get_current_user)) -> HistoryOut:
    data = new_history.model_dump(exclude={"author_id"})
    result = History(**data, author_id=user.id)
    history_out = await history_manager.create_history(result)
    await CacheInvalidationService.on_history_changed(history_id=history_out.id, author_id=user.id)
    app_logger.info_event("history_created", history_id=history_out.id, user_id=user.id)
    return history_out

@history_router.get('/',
                    summary='Получить все истории',
                    status_code=status.HTTP_200_OK,
                    responses=history_get_all_responses,
                    description=get_histories_description)
@handle_api_errors("Ошибка при получении всех историй")
async def get_histories(user: User = Depends(get_current_user),
                        pagination: tuple[int, int] = Depends(get_small_pagination)) -> Sequence[HistoryOut]:
    skip, limit = pagination
    return await history_manager.get_histories(skip, limit, me_user_id=user.id)

@history_router.post('/by-ids',
                    summary='Получить истории по списку ID',
                    status_code=status.HTTP_200_OK)
@handle_api_errors("Ошибка при получении историй по списку ID")
async def get_histories_by_ids(payload: HistoryIdsIn,
                               user: User = Depends(get_current_user)) -> Sequence[HistoryOut]:
    ids = list(dict.fromkeys([i for i in (payload.ids or []) if isinstance(i, int)]))
    if not ids:
        return []
    items = await history_manager.get_histories_by_ids(ids=ids, me_user_id=user.id)
    app_logger.info_event("histories_by_ids_fetched", user_id=user.id, count=len(ids))
    return items

@history_router.get('/following',
                    summary='Получить истории пользователей, на которых подписан пользователь',
                    status_code=status.HTTP_200_OK)
@handle_api_errors("Ошибка при получении историй пользователей, на которых подписан пользователь")
async def get_histories_by_follow(user: User = Depends(get_current_user),
                                  pagination: tuple[int, int] = Depends(get_small_pagination)) -> Sequence[HistoryOut]:
    skip, limit = pagination
    follow_rows = await followers_manager.get_following(user_id=user.id, skip=skip, limit=limit)
    following_ids = [getattr(row, 'user_id', None) for row in (follow_rows or [])]
    following_ids = [uid for uid in following_ids if isinstance(uid, int)]
    if not following_ids:
        return []
    return await history_manager.get_following_histories(
        user_id=user.id, following_user_ids=following_ids, skip=skip, limit=limit, me_user_id=user.id
    )

@history_router.get('/friends',
                    summary='Получить истории друзей пользователя',
                    status_code=status.HTTP_200_OK)
@handle_api_errors("Ошибка при получении историй друзей пользователя")
async def get_friends_histories(user: User = Depends(get_current_user),
                                pagination: tuple[int, int] = Depends(get_small_pagination)) -> Sequence[HistoryOut]:
    skip, limit = pagination
    friends = await friends_manager.get_friends(user_id=user.id, skip=skip, limit=limit)
    friend_ids = [f.friend_id if f.user_id == user.id else f.user_id for f in friends]
    return await history_manager.get_friends_histories(
        user_id=user.id, friends_ids=friend_ids, skip=skip, limit=limit, me_user_id=user.id
    )

@history_router.get('/{id}',
                    summary='Получить историю по ID',
                    status_code=status.HTTP_200_OK,
                    responses=history_get_responses,
                    description=get_history_description)
@handle_api_errors("Ошибка при получении истории")
async def get_history(id: int, user: User = Depends(get_current_user)) -> HistoryOut:
    history_out = await history_manager.get_history_by_id(id, me_user_id=user.id)
    if history_out is None:
        raise HistoryNotFoundError()
    
    await history_view_manager.add_view(user_id=user.id, history_id=id)
    
    app_logger.info_event("history_fetched", history_id=id, user_id=user.id)
    return history_out
    
@history_router.get('/{id}/comments',
                    summary='Получить все комментарии к истории',
                    status_code=status.HTTP_200_OK)
@handle_api_errors("Ошибка при получении комментариев к истории")
async def get_comments_by_history_id(id: int,
                                     user: User = Depends(get_current_user),
                                     pagination: tuple[int, int] = Depends(get_small_pagination)) -> Sequence[CommentOut]:
    skip, limit = pagination
    history = await history_manager.get_history_by_id(id, me_user_id=user.id)
    if not history:
        raise HistoryNotFoundError()
    comments = await comment_manager.get_comments_by_history_id(
        id=history.id,
        user_id=user.id,
        skip=skip,
        limit=limit
    )
    app_logger.info_event("history_comments_fetched", history_id=id, user_id=user.id, skip=skip, limit=limit)
    return comments

@history_router.put('/{id}',
                    summary='Изменить историю по ID',
                    status_code=status.HTTP_200_OK,
                    responses=history_update_responses,
                    description=update_history_description)
@handle_api_errors("Ошибка при обновлении истории")
async def update_history(id: int,
                         history_update: HistoryUpdate,
                         history: History = Depends(ensure_ownership_or_moderation)) -> HistoryOut:
    await history_manager.update_obj(id=id, updated_obj=history_update)
    await CacheInvalidationService.on_history_changed(history_id=id, author_id=history.author_id)
    history_out = await history_manager.get_history_by_id(id)
    if history_out is None:
        raise HistoryNotFoundError()
    app_logger.info_event("history_updated", history_id=id, user_id=history.author_id)
    return history_out

@history_router.patch('/{id}/files',
                     summary='Добавить файлы к истории',
                     status_code=status.HTTP_200_OK,
                     responses=history_update_responses,
                     description='Добавить файлы к существующим вложениям истории.')
@handle_api_errors("Ошибка при добавлении файлов к истории")
async def add_history_files(id: int,
                           files_update: HistoryFilesUpdate,
                           history: History = Depends(ensure_ownership_or_moderation)) -> HistoryOut:
    await history_manager.add_history_files(id=id, attached_file_ids=files_update.attached_file_ids)
    await CacheInvalidationService.on_history_changed(history_id=id, author_id=history.author_id)
    history_out = await history_manager.get_history_by_id(id)
    if history_out is None:
        raise HistoryNotFoundError()
    app_logger.info_event("history_files_added", history_id=id, user_id=history.author_id, file_count=len(files_update.attached_file_ids))
    return history_out

@history_router.put('/{id}/files',
                    summary='Заменить вложения истории',
                    status_code=status.HTTP_200_OK,
                    responses=history_update_responses,
                    description='Полностью заменить вложения истории. Пустой массив открепляет все файлы.')
@handle_api_errors("Ошибка при замене вложений истории")
async def replace_history_files(id: int,
                               files_update: HistoryFilesUpdate,
                               history: History = Depends(ensure_ownership_or_moderation)) -> HistoryOut:
    await history_manager.replace_history_files(id=id, attached_file_ids=files_update.attached_file_ids)
    await CacheInvalidationService.on_history_changed(history_id=id, author_id=history.author_id)
    history_out = await history_manager.get_history_by_id(id)
    if history_out is None:
        raise HistoryNotFoundError()
    app_logger.info_event("history_files_replaced", history_id=id, user_id=history.author_id, file_count=len(files_update.attached_file_ids))
    return history_out

@history_router.delete('/{id}',
                       summary='Удалить историю по ID',
                       status_code=status.HTTP_204_NO_CONTENT,
                       responses=history_delete_responses,
                       description=delete_history_description)
@handle_api_errors("Ошибка при удалении истории")
async def delete_history(id: int,
                         history: History = Depends(ensure_ownership_or_moderation)) -> Response:
    await history_manager.delete_obj(id)
    await CacheInvalidationService.on_history_changed(history_id=id, author_id=history.author_id)
    app_logger.info_event("history_deleted", history_id=id, user_id=history.author_id)
    return Response(status_code=204)
