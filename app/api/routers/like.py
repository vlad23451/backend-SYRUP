from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from fastapi import status

from api.dependencies.auth import get_current_user

from api.docs.like import create_like_description
from api.docs.like import delete_like_description
from api.docs.like import get_like_description
from api.docs.like import like_create_responses
from api.docs.like import like_delete_responses
from api.docs.like import like_get_responses

from core.logger import app_logger

from database.models.user import User

from exceptions.likes import LikeNotFoundError

from schemas.like import HistoryLikeCreate
from schemas.like import HistoryLikeOut

from services.error_handler_service import handle_api_errors
from services.reaction_service import ReactionService

like_router = APIRouter(prefix="/likes", tags=["Лайки"])

reaction_service = ReactionService()

@like_router.post("/",
                  summary='Создать лайк истории',
                  status_code=status.HTTP_201_CREATED,
                  responses=like_create_responses,
                  description=create_like_description)
@handle_api_errors("Ошибка при создании лайка истории")
async def create_like(like: HistoryLikeCreate,
                      user: User = Depends(get_current_user)) -> HistoryLikeOut:
    data = like.model_dump()
    result = await reaction_service.create_history_like(history_id=data["history_id"], me=user)
    app_logger.info_event("history_like_created", like_id=result.id, history_id=result.history_id, user_id=user.id)
    return result

@like_router.get("/{history_id}",
                 summary='Получить мой лайк истории по ID истории',
                 status_code=status.HTTP_200_OK,
                 responses=like_get_responses,
                 description=get_like_description)
@handle_api_errors("Ошибка при получении лайка истории")
async def get_like(history_id: int,
                   user: User = Depends(get_current_user)) -> HistoryLikeOut:
    result = await reaction_service.get_history_like(history_id=history_id, me=user)
    if result is None:
        raise LikeNotFoundError()
    app_logger.info_event("history_like_fetched", like_id=result.id, history_id=history_id, user_id=user.id)
    return result

@like_router.delete("/{history_id}",
                    summary='Удалить мой лайк истории по ID истории',
                    status_code=status.HTTP_204_NO_CONTENT,
                    responses=like_delete_responses,
                    description=delete_like_description)
@handle_api_errors("Ошибка при удалении лайка истории")
async def delete_like(history_id: int, user: User = Depends(get_current_user)) -> Response:
    await reaction_service.delete_history_like(history_id=history_id, me=user)
    app_logger.info_event("history_like_deleted", history_id=history_id, user_id=user.id)
    return Response(status_code=204)
