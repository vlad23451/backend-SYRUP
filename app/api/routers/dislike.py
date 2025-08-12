from api.dependencies.auth import get_current_user
from api.docs.like import (create_like_description, delete_like_description,
                           get_like_description, like_create_responses,
                           like_delete_responses, like_get_responses)
from core.logger import app_logger
from database.models.user import User
from exceptions.base import DatabaseError
from exceptions.like import DislikeNotFoundError, OwnershipDislikeError
from fastapi import APIRouter, Depends, Response, status
from schemas.like import HistoryDislikeCreate, HistoryDislikeOut
from services.error_handler_service import handle_api_errors
from services.reaction_service import ReactionService

dislike_router = APIRouter(prefix="/dislikes", tags=["Дизлайки"])

reaction_service = ReactionService()

@dislike_router.post("/",
                     summary='Создать дизлайк истории',
                     status_code=status.HTTP_201_CREATED,
                     responses=like_create_responses,
                     description=create_like_description)
@handle_api_errors("Ошибка при создании дизлайка истории")
async def create_dislike(dislike: HistoryDislikeCreate,
                         user: User = Depends(get_current_user)) -> HistoryDislikeOut:
    data = dislike.model_dump()
    result = await reaction_service.create_history_dislike(history_id=data["history_id"], me=user)
    app_logger.info_event("history_dislike_created", dislike_id=result.id, history_id=result.history_id, user_id=user.id)
    return result

@dislike_router.get("/{history_id}",
                    summary='Получить мой дизлайк истории по ID истории',
                    status_code=status.HTTP_200_OK,
                    responses=like_get_responses,
                    description=get_like_description)
@handle_api_errors("Ошибка при получении дизлайка истории")
async def get_dislike(history_id: int,
                      user: User = Depends(get_current_user)) -> HistoryDislikeOut:
    result = await reaction_service.get_history_dislike(history_id=history_id, me=user)
    if result is None:
        raise DislikeNotFoundError()
    app_logger.info_event("history_dislike_fetched", dislike_id=result.id, history_id=history_id, user_id=user.id)
    return result

@dislike_router.delete("/{history_id}",
                       summary='Удалить мой дизлайк истории по ID истории',
                       status_code=status.HTTP_204_NO_CONTENT,
                       responses=like_delete_responses,
                       description=delete_like_description)
@handle_api_errors("Ошибка при удалении дизлайка истории")
async def delete_dislike(history_id: int, user: User = Depends(get_current_user)) -> Response:
    await reaction_service.delete_history_dislike(history_id=history_id, me=user)
    app_logger.info_event("history_dislike_deleted", history_id=history_id, user_id=user.id)
    return Response(status_code=204)
