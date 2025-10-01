from __future__ import annotations

from typing import List
from typing import Sequence

from core.logger import app_logger

from database.managers.base_manager import BaseManager

from database.models.user import User
from database.models.user_block import UserBlock

from exceptions.base import DatabaseError

from schemas.user_block import UserBlockCreate
from schemas.user_block import UserBlockOut
from schemas.user_block import UserBlockWithUsersOut
from schemas.user_block import BlockedUserOut
from schemas.user import UserShortOut
from services.avatar_service import avatar_service

from sqlalchemy import desc
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError


class UserBlockManager(BaseManager[UserBlock, None]):
    def __init__(self) -> None:
        super().__init__(UserBlock)

    async def block_user(self, blocker_id: int, blocked_user_id: int, reason: str | None = None) -> UserBlockOut | None:
        """Заблокировать пользователя."""
        try:
            # Проверяем, что пользователь не пытается заблокировать себя
            if blocker_id == blocked_user_id:
                raise ValueError("Нельзя заблокировать самого себя")
            
            # Проверяем, что блокировка еще не существует
            existing_block = await self.get_block_by_users(blocker_id, blocked_user_id)
            if existing_block:
                return None  # Блокировка уже существует
            
            async with self.manager.get_async_session() as session:
                # Создаем блокировку
                block = UserBlock(
                    blocker_id=blocker_id,
                    blocked_id=blocked_user_id,
                    reason=reason
                )
                session.add(block)
                await session.commit()
                
                app_logger.info_event(
                    "user_blocked",
                    blocker_id=blocker_id,
                    blocked_id=blocked_user_id,
                    reason=reason
                )
                
                return UserBlockOut.model_validate(block)
                
        except IntegrityError as e:
            app_logger.warning_event(
                "user_block_already_exists",
                blocker_id=blocker_id,
                blocked_id=blocked_user_id,
                error=str(e)
            )
            return None
        except Exception as e:
            app_logger.error_event(
                "user_block_error",
                blocker_id=blocker_id,
                blocked_id=blocked_user_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при блокировке пользователя: {str(e)}")

    async def unblock_user(self, blocker_id: int, blocked_user_id: int) -> bool:
        """Разблокировать пользователя."""
        try:
            async with self.manager.get_async_session() as session:
                # Находим блокировку
                query = select(UserBlock).where(
                    UserBlock.blocker_id == blocker_id,
                    UserBlock.blocked_id == blocked_user_id
                )
                result = await session.execute(query)
                block = result.scalar_one_or_none()
                
                if not block:
                    return False  # Блокировка не найдена
                
                # Удаляем блокировку
                await session.delete(block)
                await session.commit()
                
                app_logger.info_event(
                    "user_unblocked",
                    blocker_id=blocker_id,
                    blocked_id=blocked_user_id
                )
                
                return True
                
        except Exception as e:
            app_logger.error_event(
                "user_unblock_error",
                blocker_id=blocker_id,
                blocked_id=blocked_user_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при разблокировке пользователя: {str(e)}")

    async def get_block_by_users(self, blocker_id: int, blocked_user_id: int) -> UserBlockOut | None:
        """Получить блокировку между пользователями."""
        try:
            async with self.manager.get_async_session() as session:
                query = select(UserBlock).where(
                    UserBlock.blocker_id == blocker_id,
                    UserBlock.blocked_id == blocked_user_id
                )
                result = await session.execute(query)
                block = result.scalar_one_or_none()
                
                if block:
                    return UserBlockOut.model_validate(block)
                return None
                
        except Exception as e:
            app_logger.error_event(
                "user_block_get_error",
                blocker_id=blocker_id,
                blocked_id=blocked_user_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при получении блокировки: {str(e)}")

    async def get_blocked_users(self, blocker_id: int, skip: int = 0, limit: int = 50) -> tuple[Sequence[BlockedUserOut], int]:
        """Получить список заблокированных пользователей с общим количеством."""
        try:
            async with self.manager.get_async_session() as session:
                # Получаем общее количество
                count_query = select(UserBlock.id).where(UserBlock.blocker_id == blocker_id)
                count_result = await session.execute(count_query)
                total = len(count_result.scalars().all())
                
                # Получаем данные с пагинацией (только blocked пользователя)
                query = (
                    select(UserBlock)
                    .options(
                        joinedload(UserBlock.blocked)
                    )
                    .where(UserBlock.blocker_id == blocker_id)
                    .order_by(desc(UserBlock.created_at))
                    .offset(skip)
                    .limit(limit)
                )
                
                result = await session.execute(query)
                blocks = result.unique().scalars().all()
                
                # Создаем BlockedUserOut с правильной обработкой аватарок
                blocked_users = []
                for block in blocks:
                    # Создаем UserShortOut с правильным avatar_url
                    user_short = await UserShortOut.from_user(block.blocked, avatar_service)
                    
                    blocked_user = BlockedUserOut(
                        id=block.id,
                        blocked=user_short,
                        reason=block.reason,
                        created_at=block.created_at,
                        block_status="blocked_by_me"  # Текущий пользователь заблокировал этого пользователя
                    )
                    blocked_users.append(blocked_user)
                
                return blocked_users, total
                
        except Exception as e:
            app_logger.error_event(
                "blocked_users_get_error",
                blocker_id=blocker_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при получении заблокированных пользователей: {str(e)}")

    async def get_blocked_by_users_with_status(self, blocked_id: int, skip: int = 0, limit: int = 50) -> tuple[Sequence[BlockedUserOut], int]:
        """Получить список пользователей, которые заблокировали данного пользователя, с общим количеством."""
        try:
            async with self.manager.get_async_session() as session:
                # Получаем общее количество
                count_query = select(UserBlock.id).where(UserBlock.blocked_id == blocked_id)
                count_result = await session.execute(count_query)
                total = len(count_result.scalars().all())
                
                # Получаем данные с пагинацией (только blocker пользователя)
                query = (
                    select(UserBlock)
                    .options(
                        joinedload(UserBlock.blocker)
                    )
                    .where(UserBlock.blocked_id == blocked_id)
                    .order_by(desc(UserBlock.created_at))
                    .offset(skip)
                    .limit(limit)
                )
                
                result = await session.execute(query)
                blocks = result.unique().scalars().all()
                
                # Создаем BlockedUserOut с правильной обработкой аватарок
                blocked_users = []
                for block in blocks:
                    # Создаем UserShortOut с правильным avatar_url
                    user_short = await UserShortOut.from_user(block.blocker, avatar_service)
                    
                    blocked_user = BlockedUserOut(
                        id=block.id,
                        blocked=user_short,
                        reason=block.reason,
                        created_at=block.created_at,
                        block_status="blocked_me"  # Этот пользователь заблокировал текущего пользователя
                    )
                    blocked_users.append(blocked_user)
                
                return blocked_users, total
                
        except Exception as e:
            app_logger.error_event(
                "blocked_by_users_get_error",
                blocked_id=blocked_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при получении пользователей, заблокировавших данного: {str(e)}")

    async def get_blocked_by_users(self, blocked_id: int, skip: int = 0, limit: int = 50) -> Sequence[UserBlockWithUsersOut]:
        """Получить список пользователей, которые заблокировали данного пользователя."""
        try:
            async with self.manager.get_async_session() as session:
                query = (
                    select(UserBlock)
                    .options(
                        joinedload(UserBlock.blocker),
                        joinedload(UserBlock.blocked)
                    )
                    .where(UserBlock.blocked_id == blocked_id)
                    .order_by(desc(UserBlock.created_at))
                    .offset(skip)
                    .limit(limit)
                )
                
                result = await session.execute(query)
                blocks = result.unique().scalars().all()
                
                return [UserBlockWithUsersOut.model_validate(block) for block in blocks]
                
        except Exception as e:
            app_logger.error_event(
                "blocked_by_users_get_error",
                blocked_id=blocked_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при получении пользователей, заблокировавших данного: {str(e)}")

    async def is_user_blocked(self, blocker_id: int, blocked_user_id: int) -> bool:
        """Проверить, заблокирован ли пользователь."""
        try:
            block = await self.get_block_by_users(blocker_id, blocked_user_id)
            return block is not None
        except Exception as e:
            app_logger.error_event(
                "user_block_check_error",
                blocker_id=blocker_id,
                blocked_id=blocked_user_id,
                error=str(e)
            )
            return False

    async def get_block_count_by_user(self, user_id: int) -> int:
        """Получить количество заблокированных пользователей."""
        try:
            async with self.manager.get_async_session() as session:
                query = select(UserBlock.id).where(UserBlock.blocker_id == user_id)
                result = await session.execute(query)
                return len(result.scalars().all())
        except Exception as e:
            app_logger.error_event(
                "user_block_count_error",
                user_id=user_id,
                error=str(e)
            )
            return 0
