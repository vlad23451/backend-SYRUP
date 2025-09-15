"""Менеджер сообщений и чатов.

Содержит выборки сообщений по комнате, последние сообщения по комнатам,
служебные предикаты и форматирование данных в схемы ответа.
"""
from typing import List

from datetime import datetime
from datetime import timezone

from database.managers.base_manager import BaseManager
from database.managers.session_manager import manager
from database.models.message import Message

from schemas.message import MessageOut
from schemas.message import MessageUpdate
from schemas.message import ChatHistoryResponse
from services.avatar_service import avatar_service

from sqlalchemy import and_
from sqlalchemy import update
from sqlalchemy import select
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

class MessageManager(BaseManager[Message, MessageUpdate]):
    def __init__(self):
        super().__init__(Message)

    @staticmethod
    def _select_messages_by_chat(chat_id: int):
        """Выборка сообщений по ID чата."""
        return (
            select(Message)
            .where(and_(Message.chat_id == chat_id, Message.is_deleted == False))
            .order_by(Message.timestamp.desc())
            .options(joinedload(Message.sender))
        )

    @staticmethod
    def _select_last_message_by_chat(chat_id: int):
        """Выборка последнего сообщения по ID чата."""
        return select(Message).where(and_(Message.chat_id == chat_id, Message.is_deleted == False)).order_by(Message.timestamp.desc())
    
    @staticmethod
    def _format_message_out(message: Message) -> MessageOut:
        """Форматирование сообщения в схему ответа."""
        return MessageOut(id=message.id,
                          sender_id=message.sender_id,
                          chat_id=message.chat_id,
                          text=message.text,
                          timestamp=message.timestamp,
                          from_me=True,
                          message_type=getattr(message, 'message_type', 'text'),
                          is_read=getattr(message, 'is_read', False),
                          metadata=getattr(message, 'message_metadata', {}),
                          edited_at=getattr(message, 'edited_at', None),
                          is_deleted=getattr(message, 'is_deleted', False),
                          is_pinned=getattr(message, 'is_pinned', False))

    @staticmethod
    def _format_message_out_with_me(message: Message, me_user_id: int) -> MessageOut:
        """Форматирование сообщения с учётом текущего пользователя (from_me)."""
        return MessageOut(id=message.id,
                          sender_id=message.sender_id,
                          chat_id=message.chat_id,
                          text=message.text,
                          timestamp=message.timestamp,
                          from_me=(message.sender_id == me_user_id),
                          message_type=getattr(message, 'message_type', 'text'),
                          is_read=getattr(message, 'is_read', False),
                          metadata=getattr(message, 'message_metadata', {}),
                          edited_at=getattr(message, 'edited_at', None),
                          is_deleted=getattr(message, 'is_deleted', False),
                          is_pinned=getattr(message, 'is_pinned', False))

    @staticmethod
    async def save_message(message_data: dict) -> MessageOut:
        """Сохранить сообщение в базу данных и вернуть его в схеме ответа."""
        async with manager.get_async_session() as session:
            message = Message(**message_data)
            session.add(message)
            await session.commit()
            await session.refresh(message)
            
            # Загружаем связанный объект sender с avatar_key
            await session.refresh(message, ['sender'])
            return MessageManager._format_message_out(message)

    @staticmethod
    async def get_chat_history(chat_id: int) -> List[MessageOut]:
        """Получить историю сообщений в чате."""
        async with manager.get_async_session() as session:
            result = await session.execute(MessageManager._select_messages_by_chat(chat_id))
            messages = result.scalars().all()
            return [MessageManager._format_message_out(msg) for msg in messages]

    @staticmethod
    async def get_history_by_chat(chat_id: int, me_user_id: int, skip: int = 0, limit: int = 50) -> List[MessageOut]:
        """История сообщений по chat_id с пагинацией (по времени по убыванию)."""
        async with manager.get_async_session() as session:
            result = await session.execute(
                select(Message)
                .where(and_(Message.chat_id == chat_id, Message.is_deleted == False))
                .order_by(Message.timestamp.desc())
                .offset(skip)
                .limit(limit)
                .options(joinedload(Message.sender))
            )
            messages = result.scalars().all()
            return [MessageManager._format_message_out_with_me(msg, me_user_id) for msg in messages][::-1]

    @staticmethod
    async def get_chat_history_with_avatar(chat_id: int, me_user_id: int, skip: int = 0, limit: int = 50) -> ChatHistoryResponse:
        """История сообщений чата с аватаром собеседника."""
        async with manager.get_async_session() as session:
            # Получаем сообщения (исключаем удаленные)
            result = await session.execute(
                select(Message)
                .where(and_(Message.chat_id == chat_id, Message.is_deleted == False))
                .order_by(Message.timestamp.desc())
                .offset(skip)
                .limit(limit)
                .options(joinedload(Message.sender))
            )
            messages = result.scalars().all()
            
            formatted_messages = [MessageManager._format_message_out_with_me(msg, me_user_id) for msg in messages][::-1]
            
            # Получаем аватар собеседника (первого найденного отправителя, который не текущий пользователь)
            companion_avatar_url = None
            for msg in messages:
                if msg.sender_id != me_user_id and msg.sender:
                    companion_avatar_url = await avatar_service.get_avatar_url_or_none(msg.sender)
                    break
            
            return ChatHistoryResponse(
                companion_avatar_url=companion_avatar_url,
                messages=formatted_messages
            )

    @staticmethod
    async def get_last_message_by_chat_id(chat_id: int) -> Message | None:
        """Получить последнее сообщение по ID чата."""
        async with manager.get_async_session() as session:
            result_message_out = await session.execute(MessageManager._select_last_message_by_chat(chat_id))
            return result_message_out.scalars().first() 

    @staticmethod
    async def mark_read(chat_id: int, user_id: int, until_timestamp: str | None = None) -> int:
        """Пометить сообщения как прочитанные в чате для пользователя.

        until_timestamp — ISO строка. Если не задана, помечаем все сообщения в чате для этого пользователя.
        Возвращает количество обновлённых строк.
        """
        async with manager.get_async_session() as session:
            stmt = update(Message).where(
                and_(
                    Message.chat_id == chat_id,
                    Message.sender_id != user_id,
                    Message.is_read == False,
                )
            ).values(is_read=True)

            if until_timestamp:
                try:
                    ts = datetime.fromisoformat(until_timestamp)
                    stmt = stmt.where(Message.timestamp <= ts)
                except Exception:
                    pass

            result = await session.execute(stmt)
            await session.commit()
            return int(result.rowcount or 0)

    @staticmethod
    async def edit_message(message_id: int, editor_user_id: int, new_text: str) -> MessageOut:
        """Изменить текст сообщения (разрешено только автору)."""
        async with manager.get_async_session() as session:
            msg_obj = await session.get(Message, message_id)
            if not msg_obj:
                raise ValueError("Message not found")
            if msg_obj.sender_id != editor_user_id:
                raise PermissionError("Only author can edit message")
            msg_obj.text = new_text
            msg_obj.edited_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(msg_obj)
            return MessageManager._format_message_out(msg_obj)

    @staticmethod
    async def delete_message(message_id: int, requester_user_id: int) -> bool:
        """Пометить сообщение как удаленное (soft-delete)."""
        async with manager.get_async_session() as session:
            msg_obj = await session.get(Message, message_id)
            if not msg_obj:
                return False
            # Разрешение: автор или админ чата (пока допускаем только автора)
            if msg_obj.sender_id != requester_user_id:
                raise PermissionError("Only author can delete message")
            msg_obj.is_deleted = True
            await session.commit()
            return True

    @staticmethod
    async def set_pinned(message_id: int, requester_user_id: int, is_pinned: bool) -> MessageOut:
        """Закрепить/открепить сообщение (пока разрешено автору)."""
        async with manager.get_async_session() as session:
            msg_obj = await session.get(Message, message_id)
            if not msg_obj:
                raise ValueError("Message not found")
            if msg_obj.sender_id != requester_user_id:
                raise PermissionError("Only author can pin message")
            msg_obj.is_pinned = bool(is_pinned)
            await session.commit()
            await session.refresh(msg_obj)
            return MessageManager._format_message_out(msg_obj)
