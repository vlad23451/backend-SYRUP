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
from schemas.message import MessageSearchRequest
from schemas.message import MessageSearchResponse
from schemas.message import MessageSearchResult
from services.avatar_service import avatar_service

from sqlalchemy import and_
from sqlalchemy import update
from sqlalchemy import select
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy import or_
from sqlalchemy import func
from sqlalchemy import text

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
    async def _format_message_out(message: Message) -> MessageOut:
        """Форматирование сообщения в схему ответа."""
        attached_files = await MessageManager.get_attached_files(message.id)
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
                          is_pinned=getattr(message, 'is_pinned', False),
                          attached_files=attached_files)

    @staticmethod
    async def _format_message_out_with_me(message: Message, me_user_id: int) -> MessageOut:
        """Форматирование сообщения с учётом текущего пользователя (from_me)."""
        attached_files = await MessageManager.get_attached_files(message.id)
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
                          is_pinned=getattr(message, 'is_pinned', False),
                          attached_files=attached_files)

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
            return await MessageManager._format_message_out(message)

    @staticmethod
    async def get_chat_history(chat_id: int) -> List[MessageOut]:
        """Получить историю сообщений в чате."""
        async with manager.get_async_session() as session:
            result = await session.execute(MessageManager._select_messages_by_chat(chat_id))
            messages = result.scalars().all()
            return [await MessageManager._format_message_out(msg) for msg in messages]

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
            formatted_messages = []
            for msg in messages:
                formatted_msg = await MessageManager._format_message_out_with_me(msg, me_user_id)
                formatted_messages.append(formatted_msg)
            return formatted_messages

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
            
            formatted_messages = []
            for msg in messages:
                formatted_msg = await MessageManager._format_message_out_with_me(msg, me_user_id)
                formatted_messages.append(formatted_msg)
            
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
            return await MessageManager._format_message_out(msg_obj)

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
            return await MessageManager._format_message_out(msg_obj)

    @staticmethod
    async def search_messages(search_request: MessageSearchRequest, user_id: int) -> MessageSearchResponse:
        """Поиск сообщений по тексту с фильтрацией."""
        from database.managers.chat_manager import ChatManager
        from database.managers.user_manager import UserManager
        
        async with manager.get_async_session() as session:
            # Получаем чаты пользователя, если chat_id не указан
            if search_request.chat_id:
                # Проверяем, что пользователь является участником чата
                if not await ChatManager.is_participant(search_request.chat_id, user_id):
                    return MessageSearchResponse(
                        results=[],
                        total_count=0,
                        has_more=False,
                        query=search_request.query
                    )
                chat_ids = [search_request.chat_id]
            else:
                chat_ids = await ChatManager.get_chat_ids_by_user_id(user_id)
                if not chat_ids:
                    return MessageSearchResponse(
                        results=[],
                        total_count=0,
                        has_more=False,
                        query=search_request.query
                    )
            
            # Строим базовый запрос
            query_conditions = [
                Message.chat_id.in_(chat_ids),
                Message.is_deleted == False,
                func.lower(Message.text).contains(func.lower(search_request.query))
            ]
            
            # Добавляем фильтры
            if search_request.message_type:
                query_conditions.append(Message.message_type == search_request.message_type.value)
            
            if search_request.date_from:
                query_conditions.append(Message.timestamp >= search_request.date_from)
            
            if search_request.date_to:
                query_conditions.append(Message.timestamp <= search_request.date_to)
            
            # Запрос для подсчета общего количества
            count_query = select(func.count(Message.id)).where(and_(*query_conditions))
            count_result = await session.execute(count_query)
            total_count = count_result.scalar() or 0
            
            # Запрос для получения результатов с пагинацией
            search_query = (
                select(Message)
                .where(and_(*query_conditions))
                .order_by(Message.timestamp.desc())
                .offset(search_request.offset)
                .limit(search_request.limit + 1)  # +1 для проверки has_more
                .options(joinedload(Message.sender))
            )
            
            search_result = await session.execute(search_query)
            messages = search_result.scalars().all()
            
            # Проверяем, есть ли еще результаты
            has_more = len(messages) > search_request.limit
            if has_more:
                messages = messages[:-1]  # Убираем лишний результат
            
            # Формируем результаты поиска
            search_results = []
            for message in messages:
                # Получаем информацию о чате
                chat = await ChatManager.get_chat_by_id(message.chat_id)
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
                
                # Получаем контекст (соседние сообщения)
                context_before, context_after = await MessageManager._get_message_context(
                    session, message, search_request.query
                )
                
                search_result = MessageSearchResult(
                    message=await MessageManager._format_message_out_with_me(message, user_id),
                    chat_title=chat_title,
                    companion_login=companion_login,
                    companion_avatar_url=companion_avatar_url,
                    context_before=context_before,
                    context_after=context_after
                )
                search_results.append(search_result)
            
            return MessageSearchResponse(
                results=search_results,
                total_count=total_count,
                has_more=has_more,
                query=search_request.query
            )

    @staticmethod
    async def _get_message_context(session, message: Message, query: str, context_length: int = 50) -> tuple[str | None, str | None]:
        """Получить контекст до и после найденного сообщения."""
        try:
            # Контекст до
            before_query = (
                select(Message.text)
                .where(
                    and_(
                        Message.chat_id == message.chat_id,
                        Message.timestamp < message.timestamp,
                        Message.is_deleted == False
                    )
                )
                .order_by(Message.timestamp.desc())
                .limit(1)
            )
            before_result = await session.execute(before_query)
            before_text = before_result.scalar()
            context_before = before_text[:context_length] + "..." if before_text and len(before_text) > context_length else before_text
            
            # Контекст после
            after_query = (
                select(Message.text)
                .where(
                    and_(
                        Message.chat_id == message.chat_id,
                        Message.timestamp > message.timestamp,
                        Message.is_deleted == False
                    )
                )
                .order_by(Message.timestamp.asc())
                .limit(1)
            )
            after_result = await session.execute(after_query)
            after_text = after_result.scalar()
            context_after = after_text[:context_length] + "..." if after_text and len(after_text) > context_length else after_text
            
            return context_before, context_after
        except Exception:
            return None, None

    @staticmethod
    async def get_attached_files(message_id: int) -> List[int]:
        """Получить список ID прикрепленных файлов для сообщения."""
        from database.managers.private_media_file_manager import PrivateMediaFileManager
        
        try:
            private_media_manager = PrivateMediaFileManager()
            files = await private_media_manager.get_by_message_id(message_id)
            return [file.id for file in files]
        except Exception:
            return []
