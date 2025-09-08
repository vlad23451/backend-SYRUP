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
from exceptions.like import CommentLikeNotFoundError

from schemas.like import CommentLikeCreate
from schemas.like import CommentLikeOut

from services.error_handler_service import handle_api_errors
from services.reaction_service import ReactionService

comment_like_router = APIRouter(prefix="/comment-likes", tags=["Лайки комментариев"])

reaction_service = ReactionService()

@comment_like_router.post("/",
                          summary='Создать лайк комментария',
                          status_code=status.HTTP_201_CREATED,
                          responses=like_create_responses,
                          description=create_like_description)
@handle_api_errors("Ошибка при создании лайка комментария")
async def create_comment_like(like: CommentLikeCreate,
                             user: User = Depends(get_current_user)) -> CommentLikeOut:
    data = like.model_dump()
    result = await reaction_service.create_comment_like(comment_id=data["comment_id"], me=user)
    app_logger.info_event("comment_like_created", like_id=result.id, comment_id=result.comment_id, user_id=user.id)
    return result

@comment_like_router.get("/{comment_id}",
                         summary='Получить мой лайк комментария по ID комментария',
                         status_code=status.HTTP_200_OK,
                         responses=like_get_responses,
                         description=get_like_description)
@handle_api_errors("Ошибка при получении лайка комментария")
async def get_comment_like(comment_id: int,
                          user: User = Depends(get_current_user)) -> CommentLikeOut:
    result = await reaction_service.get_comment_like(comment_id=comment_id, me=user)
    if result is None:
        raise CommentLikeNotFoundError()
    app_logger.info_event("comment_like_fetched", like_id=result.id, comment_id=comment_id, user_id=user.id)
    return result

@comment_like_router.delete("/{comment_id}",
                            summary='Удалить мой лайк комментария по ID комментария',
                            status_code=status.HTTP_204_NO_CONTENT,
                            responses=like_delete_responses,
                            description=delete_like_description)
@handle_api_errors("Ошибка при удалении лайка комментария")
async def delete_comment_like(comment_id: int, user: User = Depends(get_current_user)) -> Response:
    await reaction_service.delete_comment_like(comment_id=comment_id, me=user)
    app_logger.info_event("comment_like_deleted", comment_id=comment_id, user_id=user.id)
    return Response(status_code=204)
