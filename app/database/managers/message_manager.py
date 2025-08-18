"""Менеджер сообщений и чатов.

Содержит выборки сообщений по комнате, последние сообщения по комнатам,
служебные предикаты и форматирование данных в схемы ответа.
"""
from typing import List, Optional

from database.managers.base_manager import BaseManager
from database.managers.session_manager import manager
from database.models.message import Message
from schemas.message import MessageOut
from schemas.message import MessageUpdate
from sqlalchemy import and_, update
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

class MessageManager(BaseManager[Message, MessageUpdate]):
    def __init__(self):
        super().__init__(Message)

    @staticmethod
    def _select_messages_by_room(room_id: str):
        """Выборка сообщений по ID комнаты."""
        return (
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(Message.timestamp.desc())
            .options(joinedload(Message.sender))
        )

    @staticmethod
    def _select_last_message_per_room_for_user(user_id: int):
        """Выборка последнего сообщения по комнатам для пользователя."""
        # Подзапрос для получения последнего сообщения в каждой комнате
        subquery = (
            select(Message.room_id, func.max(Message.timestamp).label("max_timestamp"))
            .where(or_(Message.sender_id == user_id, Message.receiver_id == user_id))
            .group_by(Message.room_id)
            .subquery()
        )
        return (
            select(Message)
            .join(subquery, and_(Message.room_id == subquery.c.room_id,
                                 Message.timestamp == subquery.c.max_timestamp))
            .options(joinedload(Message.sender))
            .options(joinedload(Message.receiver))
        )

    @staticmethod
    def _select_room_ids_by_user(user_id: int):
        """Выборка уникальных ID комнат для пользователя."""
        return select(Message.room_id).where(Message.sender_id == user_id).distinct(Message.room_id)

    @staticmethod
    def _select_last_message_by_room(room_id: str):
        """Выборка последнего сообщения по ID комнаты."""
        return select(Message).where(Message.room_id == room_id).order_by(Message.timestamp.desc())

    @staticmethod
    def _get_chat_filter(user1_id: int, user2_id: int):
        """Фильтр для выборки сообщений между двумя пользователями."""
        return or_(
            and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
            and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
        )
    
    @staticmethod
    async def _format_message_out(message: Message) -> MessageOut:
        """Форматирование сообщения в схему ответа."""
        return MessageOut(id=message.id,
                          sender_id=message.sender_id,
                          receiver_id=message.receiver_id,
                          text=message.text,
                          timestamp=message.timestamp,
                          from_me=True,
                          message_type=getattr(message, 'message_type', 'text'),
                          is_read=getattr(message, 'is_read', False),
                          metadata=getattr(message, 'message_metadata', {}))

    @staticmethod
    async def _format_message_out_with_me(message: Message, me_user_id: int) -> MessageOut:
        """Форматирование сообщения с учётом текущего пользователя (from_me)."""
        return MessageOut(id=message.id,
                          sender_id=message.sender_id,
                          receiver_id=message.receiver_id,
                          room_id=message.room_id,
                          text=message.text,
                          timestamp=message.timestamp,
                          from_me=(message.sender_id == me_user_id),
                          message_type=getattr(message, 'message_type', 'text'),
                          is_read=getattr(message, 'is_read', False),
                          metadata=getattr(message, 'message_metadata', {}))

    @staticmethod
    async def _format_chat_preview(message: Message, current_user_id: int) -> dict:
        """Форматирование последнего сообщения в чате."""
        companion = message.sender if message.receiver_id == current_user_id else message.receiver
        return {"room_id": message.room_id,
                "companion_id": companion.id,
                "companion_login": companion.login,
                "last_message": (message.text or "")[:100],
                "last_message_time": message.timestamp,
                "from_me": message.sender_id == current_user_id,
                "is_read": message.is_read
        }

    @staticmethod
    async def save_message(message_data: dict) -> MessageOut:
        """Сохранить сообщение в базу данных и вернуть его в схему ответа."""
        async with manager.get_async_session() as session:
            message = Message(**message_data)
            session.add(message)
            await session.commit()
            await session.refresh(message)
            return await MessageManager._format_message_out(message)

    @staticmethod
    async def get_chat_history(room_id: str) -> List[MessageOut]:
        """Получить историю сообщений в комнате."""
        async with manager.get_async_session() as session:
            result = await session.execute(MessageManager._select_messages_by_room(room_id))
            messages = result.scalars().all()
            return [await MessageManager._format_message_out(msg) for msg in messages]

    @staticmethod
    async def get_history_by_room(room_id: str, me_user_id: int, skip: int = 0, limit: int = 50) -> List[MessageOut]:
        """История сообщений по room_id с пагинацией (по времени по убыванию)."""
        async with manager.get_async_session() as session:
            result = await session.execute(
                select(Message)
                .where(Message.room_id == room_id)
                .order_by(Message.timestamp.desc())
                .offset(skip)
                .limit(limit)
            )
            messages = result.scalars().all()
            return [await MessageManager._format_message_out_with_me(msg, me_user_id) for msg in messages]

    @staticmethod
    async def get_history_with_user(user1_id: int, user2_id: int, me_user_id: int, skip: int = 0, limit: int = 50) -> List[MessageOut]:
        """История сообщений между двумя пользователями с пагинацией."""
        async with manager.get_async_session() as session:
            result = await session.execute(
                select(Message)
                .where(MessageManager._get_chat_filter(user1_id, user2_id))
                .order_by(Message.timestamp.desc())
                .offset(skip)
                .limit(limit)
            )
            messages = result.scalars().all()
            return [await MessageManager._format_message_out_with_me(msg, me_user_id) for msg in messages]

    @staticmethod
    async def get_user_chats(user_id: int) -> List[dict]:
        """Получить последние сообщения по комнатам для пользователя."""
        async with manager.get_async_session() as session:
            result = await session.execute(MessageManager._select_last_message_per_room_for_user(user_id))
            last_messages = result.scalars().all()
            return [await MessageManager._format_chat_preview(msg, user_id) for msg in last_messages]

    @staticmethod
    async def get_room_ids_by_user_id(user_id: int) -> List[str]:
        """Получить уникальные ID комнат для пользователя."""
        async with manager.get_async_session() as session:
            result = await session.execute(MessageManager._select_room_ids_by_user(user_id))
            return list(result.scalars().all())

    @staticmethod
    async def get_last_message_by_room_id(room_id: str) -> Message | None:
        """Получить последнее сообщение по ID комнаты."""
        async with manager.get_async_session() as session:
            result_message_out = await session.execute(MessageManager._select_last_message_by_room(room_id))
            return result_message_out.scalars().first() 

    @staticmethod
    async def mark_read(room_id: str, receiver_id: int, until_timestamp: Optional[str] = None) -> int:
        """Пометить сообщения как прочитанные в комнате для получателя.

        until_timestamp — ISO строка. Если не задана, помечаем все сообщения в комнате для этого получателя.
        Возвращает количество обновлённых строк.
        """
        async with manager.get_async_session() as session:
            stmt = update(Message).where(
                and_(
                    Message.room_id == room_id,
                    Message.receiver_id == receiver_id,
                    Message.is_read == False,  # noqa: E712
                )
            ).values(is_read=True)

            if until_timestamp:
                try:
                    # сравнение по строке времени — полагаемся на формат ISO и хранение в UTC
                    # SQLAlchemy сам подставит корректный тип
                    from datetime import datetime
                    ts = datetime.fromisoformat(until_timestamp)
                    stmt = stmt.where(Message.timestamp <= ts)
                except Exception:
                    # если парсинг не удался — отметим без ограничения по времени
                    pass

            result = await session.execute(stmt)
            await session.commit()
            return int(result.rowcount or 0)
