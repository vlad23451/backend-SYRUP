from typing import List
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from fastapi import status

from api.dependencies.auth import get_current_user
from api.dependencies.ownership import get_comment_or_error

from api.docs.comment import comment_create_responses
from api.docs.comment import comment_delete_responses
from api.docs.comment import comment_get_responses
from api.docs.comment import comment_update_responses
from api.docs.comment import create_comment_description
from api.docs.comment import delete_comment_description
from api.docs.comment import get_comment_description
from api.docs.comment import update_comment_description
from api.docs.comment import add_comment_files_description
from api.docs.comment import replace_comment_files_description

from schemas.media import MediaFileResponse
from core.logger import app_logger

from database.managers.comment_manager import CommentManager
from database.models.comments import Comment
from database.models.user import User

from schemas.comment import CommentCreate
from schemas.comment import CommentOut
from schemas.comment import CommentUpdate
from schemas.comment import CommentFilesUpdate

from services.cache_invalidation_service import CacheInvalidationService
from services.error_handler_service import handle_api_errors
from services.reaction_service import ReactionService

comment_router = APIRouter(prefix="/comments", tags=["Комментарии"])

reaction_service = ReactionService()
comment_manager = CommentManager()

@comment_router.post("/",
                     summary='Создать комментарий',
                     status_code=status.HTTP_201_CREATED,
                     responses=comment_create_responses,
                     description=create_comment_description)
@handle_api_errors("Ошибка при создании комментария")
async def create_comment(comment: CommentCreate,
                         user: User = Depends(get_current_user)) -> CommentOut:
    user_info = await reaction_service.build_comment_user_info(me_user_id=user.id, author_user_id=user.id)

    new_comment = Comment(**comment.model_dump(), user_id=user.id)
    created_comment = await comment_manager.create_obj(obj=new_comment)
    await CacheInvalidationService.on_comment_changed(history_id=created_comment.history_id)
    app_logger.info(f"Комментарий {created_comment.id} создан пользователем {user.id}")
    return CommentOut(
        id=created_comment.id,
        content=created_comment.content,
        created_at=created_comment.created_at,
        updated_at=created_comment.updated_at,
        comment_type=created_comment.comment_type,
        comment_metadata=created_comment.comment_metadata,
        user_info=user_info
    )

@comment_router.get("/{id}",
                    summary='Получить комментарий по ID',
                    status_code=status.HTTP_200_OK,
                    responses=comment_get_responses,
                    description=get_comment_description)
@handle_api_errors("Ошибка при получении комментария")
async def get_comment(id: int,
                      user: User = Depends(get_current_user)) -> CommentOut:
    comment = await get_comment_or_error(id, user)
    user_info = await reaction_service.build_comment_user_info(me_user_id=user.id, author_user_id=comment.user_id)
    likes_count, dislikes_count = await comment_manager._get_single_like_dislike_counts(comment.id)
    liked_users, disliked_users = await comment_manager._get_users_for_comment(comment.id, me_user_id=user.id)
    
    attached_files_data = await comment_manager.get_attached_files(comment.id)
    attached_files = [MediaFileResponse(**file_data) for file_data in attached_files_data]
    
    app_logger.info(f"Комментарий {comment.id} получен пользователем {user.id}")
    return CommentOut(
        id=comment.id,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        comment_type=comment.comment_type,
        comment_metadata=comment.comment_metadata,
        user_info=user_info,
        likes=likes_count,
        dislikes=dislikes_count,
        liked_users=liked_users,
        disliked_users=disliked_users,
        attached_files=attached_files
    )

@comment_router.put("/{id}",
                    summary='Изменить комментарий по ID',
                    status_code=status.HTTP_200_OK,
                    responses=comment_update_responses,
                    description=update_comment_description)
@handle_api_errors("Ошибка при обновлении комментария")
async def update_comment(id: int,
                         comment_update: CommentUpdate,
                         user: User = Depends(get_current_user)) -> CommentOut:
    await get_comment_or_error(id, user)
    updated_comment = await comment_manager.update_obj(id, comment_update)
    
    user_info = await reaction_service.build_comment_user_info(me_user_id=user.id, author_user_id=updated_comment.user_id)
    
    likes_count, dislikes_count = await comment_manager._get_single_like_dislike_counts(updated_comment.id)
    liked_users, disliked_users = await comment_manager._get_users_for_comment(updated_comment.id, me_user_id=user.id)

    attached_files_data = await comment_manager.get_attached_files(updated_comment.id)
    attached_files = [MediaFileResponse(**file_data) for file_data in attached_files_data]

    await CacheInvalidationService.on_comment_changed(history_id=updated_comment.history_id)
    app_logger.info(f"Комментарий {updated_comment.id} обновлен пользователем {user.id}")
    return CommentOut(
        id=updated_comment.id,
        content=updated_comment.content,
        created_at=updated_comment.created_at,
        updated_at=updated_comment.updated_at,
        comment_type=updated_comment.comment_type,
        comment_metadata=updated_comment.comment_metadata,
        user_info=user_info,
        likes=likes_count,
        dislikes=dislikes_count,
        liked_users=liked_users,
        disliked_users=disliked_users,
        attached_files=attached_files
    )

@comment_router.delete("/{id}",
                       summary='Удалить комментарий по ID',
                       status_code=status.HTTP_204_NO_CONTENT,
                       responses=comment_delete_responses,
                       description=delete_comment_description)
@handle_api_errors("Ошибка при удалении комментария")
async def delete_comment(id: int,
                         user: User = Depends(get_current_user)) -> Response:
    comment = await get_comment_or_error(id, user)
    await comment_manager.delete_obj(id)
    await CacheInvalidationService.on_comment_changed(history_id=comment.history_id)
    app_logger.info(f"Комментарий {id} удален пользователем {user.id}")
    return Response(status_code=204)

@comment_router.patch("/{id}/files",
                     summary='Добавить файлы к комментарию',
                     status_code=status.HTTP_200_OK,
                     responses=comment_update_responses,
                     description=add_comment_files_description)
@handle_api_errors("Ошибка при добавлении файлов к комментарию")
async def add_comment_files(id: int,
                           files_update: CommentFilesUpdate,
                           user: User = Depends(get_current_user)) -> CommentOut:
    await get_comment_or_error(id, user)
    await comment_manager.add_comment_files(id=id, attached_file_ids=files_update.attached_file_ids)
    
    updated_comment = await comment_manager.get_obj_by_id(id)
    user_info = await reaction_service.build_comment_user_info(me_user_id=user.id, author_user_id=updated_comment.user_id)
    
    likes_count, dislikes_count = await comment_manager._get_single_like_dislike_counts(updated_comment.id)
    liked_users, disliked_users = await comment_manager._get_users_for_comment(updated_comment.id, me_user_id=user.id)

    attached_files_data = await comment_manager.get_attached_files(updated_comment.id)
    attached_files = [MediaFileResponse(**file_data) for file_data in attached_files_data]

    await CacheInvalidationService.on_comment_changed(history_id=updated_comment.history_id)
    app_logger.info(f"Файлы добавлены к комментарию {id} пользователем {user.id}")
    return CommentOut(
        id=updated_comment.id,
        content=updated_comment.content,
        created_at=updated_comment.created_at,
        updated_at=updated_comment.updated_at,
        comment_type=updated_comment.comment_type,
        comment_metadata=updated_comment.comment_metadata,
        user_info=user_info,
        likes=likes_count,
        dislikes=dislikes_count,
        liked_users=liked_users,
        disliked_users=disliked_users,
        attached_files=attached_files
    )

@comment_router.put("/{id}/files",
                    summary='Заменить вложения комментария',
                    status_code=status.HTTP_200_OK,
                    responses=comment_update_responses,
                    description=replace_comment_files_description)
@handle_api_errors("Ошибка при замене вложений комментария")
async def replace_comment_files(id: int,
                               files_update: CommentFilesUpdate,
                               user: User = Depends(get_current_user)) -> CommentOut:
    await get_comment_or_error(id, user)
    await comment_manager.replace_comment_files(id=id, attached_file_ids=files_update.attached_file_ids)
    
    updated_comment = await comment_manager.get_obj_by_id(id)
    user_info = await reaction_service.build_comment_user_info(me_user_id=user.id, author_user_id=updated_comment.user_id)
    
    likes_count, dislikes_count = await comment_manager._get_single_like_dislike_counts(updated_comment.id)
    liked_users, disliked_users = await comment_manager._get_users_for_comment(updated_comment.id, me_user_id=user.id)

    attached_files_data = await comment_manager.get_attached_files(updated_comment.id)
    attached_files = [MediaFileResponse(**file_data) for file_data in attached_files_data]

    await CacheInvalidationService.on_comment_changed(history_id=updated_comment.history_id)
    app_logger.info(f"Вложения комментария {id} заменены пользователем {user.id}")
    return CommentOut(
        id=updated_comment.id,
        content=updated_comment.content,
        created_at=updated_comment.created_at,
        updated_at=updated_comment.updated_at,
        comment_type=updated_comment.comment_type,
        comment_metadata=updated_comment.comment_metadata,
        user_info=user_info,
        likes=likes_count,
        dislikes=dislikes_count,
        liked_users=liked_users,
        disliked_users=disliked_users,
        attached_files=attached_files
    )

