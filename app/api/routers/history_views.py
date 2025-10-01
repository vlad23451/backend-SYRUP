from typing import List
from typing import Sequence

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from api.dependencies.auth import get_current_user
from api.dependencies.pagination import get_small_pagination

from database.managers.history_view_manager import HistoryViewManager
from database.models.user import User

from exceptions.history_views import HistoryViewNotFoundError

from schemas.history_view import HistoryViewCreate
from schemas.history_view import HistoryViewsBulkCreate
from schemas.history_view import HistoryViewOut
from schemas.history_view import HistoryViewWithHistoryOut
from schemas.history_view import HistoryViewWithUserOut

from services.error_handler_service import handle_api_errors

from core.logger import app_logger

history_views_router = APIRouter(prefix='/history-views', tags=['Просмотры историй'])

history_view_manager = HistoryViewManager()

@history_views_router.post('/',
                          summary='Добавить просмотр истории',
                          status_code=status.HTTP_201_CREATED,
                          description='Добавить просмотр истории пользователем. Просмотры уникальны - один пользователь может просмотреть одну историю только один раз.')
@handle_api_errors("Ошибка при добавлении просмотра истории")
async def add_history_view(view_data: HistoryViewCreate,
                          user: User = Depends(get_current_user)) -> HistoryViewOut:
    view = await history_view_manager.add_view(
        user_id=user.id,
        history_id=view_data.history_id
    )
    
    if view is None:
        # Просмотр уже существует, возвращаем существующий
        existing_view = await history_view_manager.get_view_by_user_and_history(
            user_id=user.id,
            history_id=view_data.history_id
        )
        if existing_view:
            return existing_view
        else:
            raise HistoryViewNotFoundError()
    
    app_logger.info_event("history_view_created", user_id=user.id, history_id=view_data.history_id)
    return view

@history_views_router.post('/bulk',
                          summary='Добавить просмотры для списка историй',
                          status_code=status.HTTP_201_CREATED,
                          description='Добавить просмотры для нескольких историй одним запросом. Просмотры уникальны - один пользователь может просмотреть одну историю только один раз.')
@handle_api_errors("Ошибка при массовом добавлении просмотров историй")
async def add_history_views_bulk(view_data: HistoryViewsBulkCreate,
                                user: User = Depends(get_current_user)) -> List[HistoryViewOut]:
    views = await history_view_manager.add_views_bulk(
        user_id=user.id,
        history_ids=view_data.history_ids
    )
    
    app_logger.info_event("history_views_bulk_created", 
                         user_id=user.id, 
                         history_ids=view_data.history_ids,
                         count=len(views))
    return views

@history_views_router.get('/my',
                         summary='Получить мои просмотры историй',
                         status_code=status.HTTP_200_OK,
                         description='Получить все просмотры историй текущего пользователя с информацией об историях.')
@handle_api_errors("Ошибка при получении просмотров пользователя")
async def get_my_history_views(user: User = Depends(get_current_user),
                              pagination: tuple[int, int] = Depends(get_small_pagination)) -> Sequence[HistoryViewWithHistoryOut]:
    skip, limit = pagination
    views = await history_view_manager.get_user_views(
        user_id=user.id,
        skip=skip,
        limit=limit
    )
    
    app_logger.info_event("user_history_views_fetched", user_id=user.id, count=len(views))
    return views

@history_views_router.get('/history/{history_id}',
                         summary='Получить просмотры истории',
                         status_code=status.HTTP_200_OK,
                         description='Получить все просмотры конкретной истории с информацией о пользователях.')
@handle_api_errors("Ошибка при получении просмотров истории")
async def get_history_views(history_id: int,
                           user: User = Depends(get_current_user),
                           pagination: tuple[int, int] = Depends(get_small_pagination)) -> Sequence[HistoryViewWithUserOut]:
    skip, limit = pagination
    views = await history_view_manager.get_history_views(
        history_id=history_id,
        skip=skip,
        limit=limit
    )
    
    app_logger.info_event("history_views_fetched", history_id=history_id, user_id=user.id, count=len(views))
    return views

@history_views_router.get('/history/{history_id}/count',
                         summary='Получить количество просмотров истории',
                         status_code=status.HTTP_200_OK,
                         description='Получить общее количество просмотров конкретной истории.')
@handle_api_errors("Ошибка при получении количества просмотров истории")
async def get_history_views_count(history_id: int,
                                 user: User = Depends(get_current_user)) -> dict:
    count = await history_view_manager.get_views_count_by_history(history_id)
    
    app_logger.info_event("history_views_count_fetched", history_id=history_id, user_id=user.id, count=count)
    return {"history_id": history_id, "views_count": count}

@history_views_router.get('/my/count',
                         summary='Получить количество моих просмотров',
                         status_code=status.HTTP_200_OK,
                         description='Получить общее количество просмотров текущего пользователя.')
@handle_api_errors("Ошибка при получении количества просмотров пользователя")
async def get_my_views_count(user: User = Depends(get_current_user)) -> dict:
    count = await history_view_manager.get_views_count_by_user(user.id)
    
    app_logger.info_event("user_views_count_fetched", user_id=user.id, count=count)
    return {"user_id": user.id, "views_count": count}

@history_views_router.get('/check/{history_id}',
                         summary='Проверить, просматривал ли пользователь историю',
                         status_code=status.HTTP_200_OK,
                         description='Проверить, просматривал ли текущий пользователь конкретную историю.')
@handle_api_errors("Ошибка при проверке просмотра истории")
async def check_history_view(history_id: int,
                            user: User = Depends(get_current_user)) -> dict:
    view = await history_view_manager.get_view_by_user_and_history(
        user_id=user.id,
        history_id=history_id
    )
    
    has_viewed = view is not None
    viewed_at = view.viewed_at if view else None
    
    app_logger.info_event("history_view_checked", user_id=user.id, history_id=history_id, has_viewed=has_viewed)
    return {
        "history_id": history_id,
        "has_viewed": has_viewed,
        "viewed_at": viewed_at
    }
