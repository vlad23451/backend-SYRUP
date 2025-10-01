from typing import List
from datetime import datetime

from database.managers.base_manager import BaseManager
from database.managers.session_manager import manager
from database.managers.chat_manager import ChatManager
from database.managers.user_manager import UserManager

from database.models.pinned_message import PinnedMessage
from database.models.message import Message
from database.models.user import User

from schemas.pinned_message import PinnedMessageCreate
from schemas.pinned_message import PinnedMessageUpdate
from schemas.pinned_message import PinnedMessageWithContext
from schemas.pinned_message import PinnedMessageListResponse
from schemas.user import UserShortOutWithFollowStatus

from services.avatar_service import avatar_service
from services.user_info_service import build_user_info

from sqlalchemy import and_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import joinedload

from core.logger import app_logger

class PinnedMessageManager(BaseManager[PinnedMessage, PinnedMessageUpdate]):
    def __init__(self):
        super().__init__(PinnedMessage)

    async def pin_message(self, message_id: int, chat_id: int, user_id: int) -> PinnedMessage:
        """Закрепить сообщение в чате"""
        async with manager.get_async_session() as session:
            try:
                # Проверяем, что сообщение существует и принадлежит чату
                message = await session.get(Message, message_id)
                if not message or message.chat_id != chat_id:
                    raise ValueError("Сообщение не найдено или не принадлежит чату")
                
                # Проверяем, что пользователь является участником чата
                if not await ChatManager.is_participant(chat_id, user_id):
                    raise PermissionError("Пользователь не является участником чата")
                
                # Проверяем, не закреплено ли уже сообщение
                existing_pin = await session.execute(
                    select(PinnedMessage).where(
                        and_(
                            PinnedMessage.message_id == message_id,
                            PinnedMessage.chat_id == chat_id
                        )
                    )
                )
                if existing_pin.scalar_one_or_none():
                    raise ValueError("Сообщение уже закреплено")
                
                # Создаем закрепление
                pinned_message = PinnedMessage(
                    message_id=message_id,
                    chat_id=chat_id,
                    pinned_by_user_id=user_id
                )
                
                # Обновляем поле is_pinned в сообщении
                message.is_pinned = True
                
                session.add(pinned_message)
                await session.commit()
                await session.refresh(pinned_message)
                
                app_logger.info(f"Сообщение {message_id} закреплено в чате {chat_id} пользователем {user_id}")
                return pinned_message
                
            except Exception as e:
                await session.rollback()
                app_logger.error(f"Ошибка закрепления сообщения {message_id}: {e}")
                raise

    async def unpin_message(self, message_id: int, chat_id: int, user_id: int) -> bool:
        """Открепить сообщение"""
        async with manager.get_async_session() as session:
            try:
                # Проверяем права доступа
                if not await ChatManager.is_participant(chat_id, user_id):
                    raise PermissionError("Пользователь не является участником чата")
                
                # Находим закрепление
                pinned_message = await session.execute(
                    select(PinnedMessage).where(
                        and_(
                            PinnedMessage.message_id == message_id,
                            PinnedMessage.chat_id == chat_id
                        )
                    )
                )
                pinned_message = pinned_message.scalar_one_or_none()
                
                if not pinned_message:
                    return False
                
                # Получаем сообщение и обновляем поле is_pinned
                message = await session.get(Message, message_id)
                if message:
                    message.is_pinned = False
                
                # Удаляем закрепление
                await session.delete(pinned_message)
                await session.commit()
                
                app_logger.info(f"Сообщение {message_id} откреплено в чате {chat_id} пользователем {user_id}")
                return True
                
            except Exception as e:
                await session.rollback()
                app_logger.error(f"Ошибка открепления сообщения {message_id}: {e}")
                raise

    async def get_pinned_messages(self, chat_id: int, user_id: int, 
                                 skip: int = 0, limit: int = 50) -> PinnedMessageListResponse:
        """Получить закрепленные сообщения чата"""
        async with manager.get_async_session() as session:
            try:
                # Проверяем права доступа
                if not await ChatManager.is_participant(chat_id, user_id):
                    raise PermissionError("Пользователь не является участником чата")
                
                # Получаем закрепленные сообщения
                query = (
                    select(PinnedMessage)
                    .where(PinnedMessage.chat_id == chat_id)
                    .order_by(PinnedMessage.pinned_at.desc())
                    .offset(skip)
                    .limit(limit)
                    .options(
                        joinedload(PinnedMessage.message).joinedload(Message.sender),
                        joinedload(PinnedMessage.pinned_by_user)
                    )
                )
                
                result = await session.execute(query)
                pinned_messages = result.scalars().all()
                
                # Получаем общее количество
                count_query = select(PinnedMessage).where(PinnedMessage.chat_id == chat_id)
                count_result = await session.execute(count_query)
                total_count = len(count_result.scalars().all())
                
                # Формируем ответ
                pinned_with_context = []
                for pinned in pinned_messages:
                    # Получаем информацию о чате
                    chat = await ChatManager.get_chat_by_id(chat_id)
                    chat_title = chat.title if chat else None
                    
                    # Для приватных чатов получаем информацию о собеседнике
                    companion_login = None
                    companion_avatar_url = None
                    if chat and chat.chat_type == 'private':
                        try:
                            if isinstance(chat.participants, str):
                                import json
                                participants = json.loads(chat.participants)
                            else:
                                participants = chat.participants
                            
                            companion_id = next((p for p in participants if p != user_id), None)
                            if companion_id:
                                companion = await UserManager().get_obj_by_id(companion_id)
                                if companion:
                                    companion_login = companion.login
                                    companion_avatar_url = await avatar_service.get_avatar_url_or_none(companion)
                        except (StopIteration, TypeError, ValueError):
                            pass
                    
                    # Формируем информацию о пользователе, закрепившем сообщение
                    pinned_by_user_info = await build_user_info(user_id, pinned.pinned_by_user)
                    
                    # Формируем сообщение
                    from schemas.message import MessageOut
                    message_out = MessageOut(
                        id=pinned.message.id,
                        sender_id=pinned.message.sender_id,
                        chat_id=pinned.message.chat_id,
                        text=pinned.message.text,
                        message_type=pinned.message.message_type,
                        timestamp=pinned.message.timestamp,
                        is_read=pinned.message.is_read,
                        metadata=pinned.message.message_metadata or {},
                        from_me=(pinned.message.sender_id == user_id),
                        edited_at=pinned.message.edited_at,
                        is_deleted=pinned.message.is_deleted,
                        is_pinned=pinned.message.is_pinned
                    )
                    
                    pinned_with_context.append(PinnedMessageWithContext(
                        id=pinned.id,
                        message=message_out,
                        chat_title=chat_title,
                        companion_login=companion_login,
                        companion_avatar_url=companion_avatar_url,
                        pinned_by_user=pinned_by_user_info,
                        pinned_at=pinned.pinned_at
                    ))
                
                return PinnedMessageListResponse(
                    pinned_messages=pinned_with_context,
                    total_count=total_count,
                    chat_id=chat_id
                )
                
            except Exception as e:
                app_logger.error(f"Ошибка получения закрепленных сообщений чата {chat_id}: {e}")
                raise


    async def is_message_pinned(self, message_id: int, chat_id: int) -> bool:
        """Проверить, закреплено ли сообщение"""
        async with manager.get_async_session() as session:
            result = await session.execute(
                select(PinnedMessage).where(
                    and_(
                        PinnedMessage.message_id == message_id,
                        PinnedMessage.chat_id == chat_id
                    )
                )
            )
            return result.scalar_one_or_none() is not None
