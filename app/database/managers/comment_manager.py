from __future__ import annotations

import asyncio
from typing import Dict
from typing import List

from core.logger import app_logger

from database.managers.base_manager import BaseManager
from database.managers.history_manager import HistoryManager
from database.managers.session_manager import Manager
from database.managers.user_manager import UserManager

from database.models.comment_like import CommentDislike
from database.models.comment_like import CommentLike
from database.models.comments import Comment
from database.models.user import User
from database.models.media_file import MediaFile

from exceptions.histories import HistoryNotFoundError
from exceptions.comments import CommentNotFoundError
from exceptions.base import DatabaseError

from schemas.comment import CommentOut, CommentUpdate
from schemas.user import UserShortOutWithFollowStatus

from services.cache_service import CommentsByHistoryCacheService
from services.user_builders_service import build_user_list
from services.user_builders_service import build_users_map
from services.user_info_service import build_user_info
from services.user_info_service import build_user_info_many
from services.media_service import MediaService
from database.managers.media_file_manager import MediaFileManager

from sqlalchemy import func
from sqlalchemy import select

manager = Manager()
user_manager = UserManager()
history_manager = HistoryManager()

class CommentManager(BaseManager[Comment, CommentUpdate]):
    def __init__(self):
        super().__init__(Comment)
        self.media_service = MediaService(MediaFileManager())

    @staticmethod
    def _select_comments_by_history(history_id: int):
        return (
            select(Comment)
            .filter_by(history_id=history_id)
            .order_by(Comment.created_at.desc())
        )

    @staticmethod
    def _select_count_for_comments(model, comment_ids: List[int]):
        return (
            select(model.comment_id, func.count(model.id).label('count'))
            .where(model.comment_id.in_(comment_ids))
            .group_by(model.comment_id)
        )

    @staticmethod
    def _select_users_for_comments(model, comment_ids: List[int]):
        return (
            select(model.comment_id, User)
            .join(User, model.user_id == User.id)
            .where(model.comment_id.in_(comment_ids))
        )

    @staticmethod
    def _select_users_for_single(model, comment_id: int):
        return (
            select(User)
            .join(model, model.user_id == User.id)
            .where(model.comment_id == comment_id)
        )

    @staticmethod
    def _select_count_for_single(model, comment_id: int):
        return select(func.count(model.id)).where(model.comment_id == comment_id)

    @staticmethod
    async def _get_like_dislike_maps(comment_ids: List[int]):
        async with manager.get_async_session() as session:
            likes_result = await session.execute(
                CommentManager._select_count_for_comments(CommentLike, comment_ids)
            )
            likes_map = {row.comment_id: row.count for row in likes_result}

            dislikes_result = await session.execute(
                CommentManager._select_count_for_comments(CommentDislike, comment_ids)
            )
            dislikes_map = {row.comment_id: row.count for row in dislikes_result}

        return likes_map, dislikes_map

    @staticmethod
    async def _get_user_maps(comment_ids: List[int],
                             me_user_id: int) -> tuple[Dict[int, List[UserShortOutWithFollowStatus]]]:
        async with manager.get_async_session() as session:
            liked_rows = await session.execute(
                CommentManager._select_users_for_comments(CommentLike, comment_ids)
            )
            disliked_rows = await session.execute(
                CommentManager._select_users_for_comments(CommentDislike, comment_ids)
            )

        liked_users_map = await build_users_map(liked_rows, me_user_id)
        disliked_users_map = await build_users_map(disliked_rows, me_user_id)
        
        return liked_users_map, disliked_users_map

    @staticmethod
    async def _get_single_like_dislike_counts(comment_id: int):
        async with manager.get_async_session() as session:
            likes_result = await session.execute(
                CommentManager._select_count_for_single(CommentLike, comment_id))
            likes_count = likes_result.scalar() or 0

            dislikes_result = await session.execute(
                CommentManager._select_count_for_single(CommentDislike, comment_id))
            dislikes_count = dislikes_result.scalar() or 0

        return likes_count, dislikes_count

    @staticmethod
    async def _get_users_for_comment(comment_id: int, me_user_id: int) -> tuple[List[UserShortOutWithFollowStatus], List[UserShortOutWithFollowStatus]]:
        async with manager.get_async_session() as session:
            liked_rows = await session.execute(CommentManager._select_users_for_single(CommentLike,
                                                                                       comment_id))
            disliked_rows = await session.execute(CommentManager._select_users_for_single(CommentDislike,
                                                                                          comment_id))

        liked_users = await build_user_list(liked_rows, me_user_id)
        disliked_users = await build_user_list(disliked_rows, me_user_id)

        return liked_users, disliked_users

    @staticmethod
    async def get_comments_by_history_id(id: int,
                                         user_id: int,
                                         skip: int = 0,
                                         limit: int = 10) -> List[CommentOut]:
        cached = await CommentsByHistoryCacheService.get_comments(history_id=id,
                                    skip=skip, limit=limit, me_user_id=user_id)
        if cached is not None:
            return cached

        history = await history_manager.get_history_by_id(id)
        if not history:
            raise HistoryNotFoundError()
        
        async with manager.get_async_session() as session:
            comments = await session.execute(
                CommentManager._select_comments_by_history(history.id).offset(skip).limit(limit)
            )
            comments = comments.scalars().all()

        comment_ids = [comment.id for comment in comments]
        likes_map_task = asyncio.create_task(CommentManager._get_like_dislike_maps(comment_ids))
        user_maps_task = asyncio.create_task(CommentManager._get_user_maps(comment_ids, me_user_id=user_id))
        # Получаем файлы для всех комментариев параллельно
        files_task = asyncio.create_task(CommentManager()._get_files_for_comments(comment_ids))
        likes_map, dislikes_map = await likes_map_task
        liked_users_map, disliked_users_map = await user_maps_task
        files_map = await files_task

        comment_outs = []

        author_ids = list({c.user_id for c in comments})
        # Параллельный сбор авторов
        authors = await asyncio.gather(*[user_manager.get_obj_by_id(uid) for uid in author_ids])
        author_info_map = await build_user_info_many(me_user_id=user_id, users=authors)

        for comment in comments:
            user_info = author_info_map.get(comment.user_id) or await build_user_info(me_user_id=user_id,
                                                  user=await user_manager.get_obj_by_id(comment.user_id))
                
            likes_count = likes_map.get(comment.id, 0)
            dislikes_count = dislikes_map.get(comment.id, 0)
            
            # Получаем прикрепленные файлы из предзагруженной карты
            attached_files = files_map.get(comment.id, [])
            
            comment_out = CommentOut.from_model_with_counts(
                comment=comment,
                user_info=user_info,
                likes_count=likes_count,
                dislikes_count=dislikes_count,
                liked_users=liked_users_map.get(comment.id, []),
                disliked_users=disliked_users_map.get(comment.id, []),
                attached_files=attached_files
            )
            comment_outs.append(comment_out)

        await CommentsByHistoryCacheService.set_comments(history_id=id,
            skip=skip, limit=limit, me_user_id=user_id, data=comment_outs)
        return comment_outs

    async def get_attached_files(self, comment_id: int) -> List[dict]:
        """Получить прикрепленные файлы комментария"""
        try:
            files = await self.media_service.get_comment_files(comment_id)
            return files
        except Exception as e:
            app_logger.error(f"Ошибка получения файлов комментария {comment_id}: {e}")
            return []

    async def attach_file_to_comment(self, comment_id: int, file_id: int, user_id: int) -> bool:
        """Прикрепить файл к комментарию"""
        try:
            # Проверяем, что комментарий принадлежит пользователю
            comment = await self.get_obj_by_id(comment_id)
            if not comment or comment.user_id != user_id:
                return False
            
            return await self.media_service.attach_to_comment(file_id, comment_id, user_id)
        except Exception as e:
            app_logger.error(f"Ошибка прикрепления файла {file_id} к комментарию {comment_id}: {e}")
            return False

    async def detach_file_from_comment(self, comment_id: int, file_id: int, user_id: int) -> bool:
        """Открепить файл от комментария"""
        try:
            # Проверяем, что комментарий принадлежит пользователю
            comment = await self.get_obj_by_id(comment_id)
            if not comment or comment.user_id != user_id:
                return False
            
            return await self.media_service.detach_from_comment(file_id, comment_id, user_id)
        except Exception as e:
            app_logger.error(f"Ошибка открепления файла {file_id} от комментария {comment_id}: {e}")
            return False

    async def _get_files_for_comments(self, comment_ids: List[int]) -> Dict[int, List]:
        """Получить файлы для списка комментариев (оптимизированно)"""
        try:
            from schemas.media import MediaFileResponse
            
            # Получаем все файлы для комментариев одним запросом
            files_data = await self.media_service.get_comment_files_batch(comment_ids)
            
            # Группируем файлы по comment_id
            files_map = {}
            for file_data in files_data:
                comment_id = file_data.get('comment_id')
                if comment_id not in files_map:
                    files_map[comment_id] = []
                files_map[comment_id].append(MediaFileResponse(**file_data))
            
            return files_map
        except Exception as e:
            app_logger.error(f"Ошибка получения файлов для комментариев: {e}")
            return {}

    async def add_comment_files(self, id: int, attached_file_ids: List[int]) -> None:
        """Добавить файлы к комментарию"""
        async with self.manager.get_async_session() as session:
            try:
                # Проверяем, что комментарий существует
                comment = await session.get(Comment, int(id))
                if not comment:
                    app_logger.error(f"Comment с id {id} не найден")
                    raise CommentNotFoundError(f"Comment с id {id} не найден")
                
                # Получаем текущие файлы комментария
                current_files_result = await session.execute(
                    select(MediaFile).where(MediaFile.comment_id == id)
                )
                current_files = current_files_result.scalars().all()
                current_file_ids = {f.id for f in current_files}
                
                # Новые файлы для прикрепления (только те, которых еще нет)
                new_file_ids = set(attached_file_ids)
                files_to_attach = new_file_ids - current_file_ids
                
                # Прикрепляем только новые файлы
                if files_to_attach:
                    from sqlalchemy import update
                    await session.execute(
                        update(MediaFile)
                        .where(MediaFile.id.in_(files_to_attach))
                        .values(comment_id=id)
                    )
                
                await session.commit()
                app_logger.info(f"Added files to comment {id}: {files_to_attach}")
            except Exception as e:
                await session.rollback()
                app_logger.exception(f"Comment files с id {id} не добавлены: {e}")
                raise DatabaseError()
    
    async def replace_comment_files(self, id: int, attached_file_ids: List[int]) -> None:
        """Полностью заменить вложения комментария"""
        async with self.manager.get_async_session() as session:
            try:
                # Проверяем, что комментарий существует
                comment = await session.get(Comment, int(id))
                if not comment:
                    app_logger.error(f"Comment с id {id} не найден")
                    raise CommentNotFoundError(f"Comment с id {id} не найден")
                
                # Получаем текущие файлы комментария
                current_files_result = await session.execute(
                    select(MediaFile).where(MediaFile.comment_id == id)
                )
                current_files = current_files_result.scalars().all()
                current_file_ids = {f.id for f in current_files}
                
                # Новые файлы для прикрепления
                new_file_ids = set(attached_file_ids)
                
                # Файлы для открепления (были прикреплены, но не в новом списке)
                files_to_detach = current_file_ids - new_file_ids
                
                # Файлы для прикрепления (в новом списке, но не были прикреплены)
                files_to_attach = new_file_ids - current_file_ids
                
                # Открепляем файлы
                if files_to_detach:
                    from sqlalchemy import update
                    await session.execute(
                        update(MediaFile)
                        .where(MediaFile.id.in_(files_to_detach))
                        .values(comment_id=None)
                    )
                
                # Прикрепляем файлы
                if files_to_attach:
                    from sqlalchemy import update
                    await session.execute(
                        update(MediaFile)
                        .where(MediaFile.id.in_(files_to_attach))
                        .values(comment_id=id)
                    )
                
                await session.commit()
                app_logger.info(f"Replaced comment {id} files: detached {files_to_detach}, attached {files_to_attach}")
            except Exception as e:
                await session.rollback()
                app_logger.exception(f"Comment files с id {id} не заменены: {e}")
                raise DatabaseError()
