from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from fastapi import status

from api.dependencies.auth import get_current_user
from api.dependencies.pagination import get_large_pagination

from api.docs.favorites import create_favorite_description
from api.docs.favorites import delete_favorite_description
from api.docs.favorites import get_favorites_description
from api.docs.favorites import check_favorite_description
from api.docs.favorites import favorite_create_responses
from api.docs.favorites import favorite_delete_responses
from api.docs.favorites import favorite_get_responses
from api.docs.favorites import favorite_check_responses

from core.logger import app_logger

from database.managers.favorites_manager import FavoritesManager

from schemas.favorites import FavoriteCreate
from schemas.favorites import FavoriteOut
from schemas.favorites import FavoritesResponse

from services.error_handler_service import handle_api_errors

from database.models.user import User

favorites_router = APIRouter(prefix="/favorites", tags=["Избранное"])

favorites_manager = FavoritesManager()


@favorites_router.post("/",
                      summary='Добавить историю в избранное',
                      status_code=status.HTTP_201_CREATED,
                      responses=favorite_create_responses,
                      description=create_favorite_description)
@handle_api_errors("Ошибка при добавлении истории в избранное")
async def add_to_favorites(favorite_data: FavoriteCreate,
                          user: User = Depends(get_current_user)) -> FavoriteOut:
    result = await favorites_manager.add_to_favorites(
        user_id=user.id,
        history_id=favorite_data.history_id
    )
    app_logger.info_event("favorite_created", favorite_id=result.id, history_id=favorite_data.history_id, user_id=user.id)
    return result

@favorites_router.delete("/{history_id}",
                        summary='Удалить историю из избранного',
                        status_code=status.HTTP_204_NO_CONTENT,
                        responses=favorite_delete_responses,
                        description=delete_favorite_description)
@handle_api_errors("Ошибка при удалении истории из избранного")
async def remove_from_favorites(history_id: int,
                                user: User = Depends(get_current_user)) -> Response:
    await favorites_manager.remove_from_favorites(
        user_id=user.id,
        history_id=history_id
    )
    app_logger.info_event("favorite_deleted", history_id=history_id, user_id=user.id)
    return Response(status_code=204) 

@favorites_router.get("/",
                     summary='Получить избранные истории пользователя',
                     status_code=status.HTTP_200_OK,
                     responses=favorite_get_responses,
                     description=get_favorites_description)
@handle_api_errors("Ошибка при получении избранных историй")
async def get_user_favorites(user: User = Depends(get_current_user),
                             pagination: tuple[int, int] = Depends(get_large_pagination)) -> FavoritesResponse:
    skip, limit = pagination
    result = await favorites_manager.get_user_favorites(
        user_id=user.id,
        skip=skip,
        limit=limit
    )
    app_logger.info_event("favorites_fetched", user_id=user.id, count=result.total, skip=skip, limit=limit)
    return result

@favorites_router.get("/check/{history_id}",
                     summary='Проверить, добавлена ли история в избранное',
                     status_code=status.HTTP_200_OK,
                     responses=favorite_check_responses,
                     description=check_favorite_description)
@handle_api_errors("Ошибка при проверке статуса избранного")
async def check_is_favorite(history_id: int,
                           user: User = Depends(get_current_user)) -> dict[str, bool]:
    is_favorite = await favorites_manager.is_favorite(
        user_id=user.id,
        history_id=history_id
    )
    app_logger.info_event("favorite_status_checked", history_id=history_id, user_id=user.id, is_favorite=is_favorite)
    return {"is_favorite": is_favorite}
