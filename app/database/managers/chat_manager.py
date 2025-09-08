from typing import List

from database.managers.base_manager import BaseManager
from database.managers.session_manager import manager
from database.managers.connection_singleton import get_connection_manager

from database.models.chat import Chat
from database.models.chat import RoomParticipant
from database.models.message import Message
from database.models.user import User

from sqlalchemy import and_
from sqlalchemy import select
from sqlalchemy.orm import joinedload

class ChatManager(BaseManager[Chat, dict]):
    def __init__(self):
        super().__init__(Chat)

    @staticmethod
    async def create_chat(participants: List[int], chat_type: str = 'private', title: str = None) -> Chat:
        """Создать новый чат с участниками."""
        async with manager.get_async_session() as session:
            chat = Chat(
                participants=participants,
                chat_type=chat_type,
                title=title
            )
            session.add(chat)
            await session.commit()
            await session.refresh(chat)
            
            for user_id in participants:
                participant = RoomParticipant(
                    chat_id=chat.id,
                    user_id=user_id,
                    is_admin=(user_id == participants[0])  # Первый участник - админ
                )
                session.add(participant)
            
            await session.commit()
            
            await ChatManager._sync_with_connection_manager(chat.id)
            
            return chat

    @staticmethod
    async def _sync_with_connection_manager(chat_id: int):
        """Синхронизировать изменения чата с ConnectionManager."""
        try:
            
            connection_manager = get_connection_manager()
            await connection_manager.sync_chat_with_db(chat_id)
        except Exception as e:
            from core.logger import app_logger
            app_logger.warning(f"Не удалось синхронизировать чат {chat_id} с ConnectionManager: {e}")

    @staticmethod
    async def get_chat_by_id(chat_id: int) -> Chat | None:
        """Получить чат по ID."""
        async with manager.get_async_session() as session:
            result = await session.execute(
                select(Chat).where(Chat.id == chat_id)
            )
            return result.scalars().first()

    @staticmethod
    async def get_private_chat_by_participants(user1_id: int, user2_id: int) -> Chat | None:
        """Найти приватный чат между двумя пользователями."""
        async with manager.get_async_session() as session:
            # Получаем все приватные чаты
            result = await session.execute(
                select(Chat).where(Chat.chat_type == 'private')
            )
            chats = result.scalars().all()
            
            # Проверяем участников
            for chat in chats:
                try:
                    if isinstance(chat.participants, str):
                        import json
                        participants = json.loads(chat.participants)
                    else:
                        participants = chat.participants
                    
                    if set(participants) == {user1_id, user2_id}:
                        return chat
                except (TypeError, ValueError):
                    continue
            
            return None

    @staticmethod
    async def get_user_chats(user_id: int) -> List[Chat]:
        """Получить все чаты пользователя."""
        async with manager.get_async_session() as session:
            # Получаем все чаты и фильтруем по участникам
            result = await session.execute(
                select(Chat).order_by(Chat.updated_at.desc())
            )
            all_chats = result.scalars().all()
            
            user_chats = []
            for chat in all_chats:
                try:
                    if isinstance(chat.participants, str):
                        import json
                        participants = json.loads(chat.participants)
                    else:
                        participants = chat.participants
                    
                    if user_id in participants:
                        user_chats.append(chat)
                except (TypeError, ValueError):
                    continue
            
            return user_chats

    @staticmethod
    async def add_participant(chat_id: int, user_id: int, is_admin: bool = False) -> bool:
        """Добавить участника в чат."""
        async with manager.get_async_session() as session:
            # Получаем чат
            chat_result = await session.execute(
                select(Chat).where(Chat.id == chat_id)
            )
            chat = chat_result.scalars().first()
            
            if not chat:
                return False
            
            # Получаем текущих участников
            try:
                if isinstance(chat.participants, str):
                    import json
                    current_participants = json.loads(chat.participants)
                else:
                    current_participants = chat.participants
            except (TypeError, ValueError):
                current_participants = []
            
            if user_id in current_participants:
                return False
            
            # Обновляем список участников
            new_participants = current_participants.copy()
            new_participants.append(user_id)
            chat.participants = new_participants
            
            # Создаем запись в RoomParticipant
            participant = RoomParticipant(
                chat_id=chat_id,
                user_id=user_id,
                is_admin=is_admin
            )
            session.add(participant)
            
            await session.commit()
            
            # Синхронизируем с ConnectionManager
            await ChatManager._sync_with_connection_manager(chat_id)
            
            return True

    @staticmethod
    async def remove_participant(chat_id: int, user_id: int) -> bool:
        """Удалить участника из чата."""
        async with manager.get_async_session() as session:
            # Получаем чат
            chat_result = await session.execute(
                select(Chat).where(Chat.id == chat_id)
            )
            chat = chat_result.scalars().first()
            
            if not chat:
                return False
            
            # Получаем текущих участников
            try:
                if isinstance(chat.participants, str):
                    import json
                    current_participants = json.loads(chat.participants)
                else:
                    current_participants = chat.participants
            except (TypeError, ValueError):
                current_participants = []
            
            if user_id not in current_participants:
                return False
            
            # Обновляем список участников
            new_participants = current_participants.copy()
            new_participants.remove(user_id)
            chat.participants = new_participants
            
            # Деактивируем участника в RoomParticipant
            participant_result = await session.execute(
                select(RoomParticipant).where(
                    and_(
                        RoomParticipant.chat_id == chat_id,
                        RoomParticipant.user_id == user_id
                    )
                )
            )
            participant = participant_result.scalars().first()
            if participant:
                participant.is_active = False
            
            await session.commit()
            
            # Синхронизируем с ConnectionManager
            await ChatManager._sync_with_connection_manager(chat_id)
            
            return True

    @staticmethod
    async def is_participant(chat_id: int, user_id: int) -> bool:
        """Проверить, является ли пользователь участником чата."""
        async with manager.get_async_session() as session:
            result = await session.execute(
                select(Chat).where(Chat.id == chat_id)
            )
            chat = result.scalars().first()
            
            if not chat:
                return False
            
            try:
                if isinstance(chat.participants, str):
                    import json
                    participants = json.loads(chat.participants)
                else:
                    participants = chat.participants
                
                return user_id in participants
            except (TypeError, ValueError):
                return False

    @staticmethod 
    async def update_chat_activity(chat_id: int):
        """Обновить время последней активности чата."""
        async with manager.get_async_session() as session:
            chat_result = await session.execute(
                select(Chat).where(Chat.id == chat_id)
            )
            chat = chat_result.scalars().first()
            if chat:
                from datetime import datetime, timezone
                chat.updated_at = datetime.now(timezone.utc)
                await session.commit()

    @staticmethod
    async def get_user_chats_with_last_messages(user_id: int) -> List[dict]:
        """Получить чаты пользователя с последними сообщениями."""
        async with manager.get_async_session() as session:
            # Получаем чаты пользователя
            user_chats = await ChatManager.get_user_chats(user_id)
            
            result = []
            for chat in user_chats:
                # Получаем последнее сообщение в чате
                last_message_result = await session.execute(
                    select(Message)
                    .where(Message.chat_id == chat.id)
                    .order_by(Message.timestamp.desc())
                    .limit(1)
                    .options(joinedload(Message.sender))
                )
                last_message = last_message_result.scalars().first()
                
                if last_message:
                    # Для приватного чата находим собеседника
                    companion_id = None
                    companion_login = None
                    
                    if chat.chat_type == 'private':
                        # Получаем участников (уже десериализованы SQLAlchemy)
                        try:
                            if isinstance(chat.participants, str):
                                import json
                                participants = json.loads(chat.participants)
                            else:
                                participants = chat.participants
                            
                            companion_id = next((p for p in participants if p != user_id), None)
                            
                            if companion_id:
                                companion_result = await session.execute(
                                    select(User).where(User.id == companion_id)
                                )
                                companion = companion_result.scalars().first()
                                if companion:
                                    companion_login = companion.login
                        except (StopIteration, TypeError, ValueError):
                            pass
                    
                    result.append({
                        "chat_id": chat.id,
                        "companion_id": companion_id,
                        "companion_login": companion_login,
                        "title": chat.title,
                        "last_message": (last_message.text or "")[:100],
                        "last_message_time": last_message.timestamp,
                        "from_me": last_message.sender_id == user_id,
                        "is_read": last_message.is_read
                    })
            
            return result

    @staticmethod
    async def create_or_get_private_chat(user1_id: int, user2_id: int) -> Chat:
        """Создать приватный чат или получить существующий."""
        # Сначала пытаемся найти существующий
        existing_chat = await ChatManager.get_private_chat_by_participants(user1_id, user2_id)
        if existing_chat:
            return existing_chat
        
        # Создаем новый
        participants = sorted([user1_id, user2_id])  # Сортируем для консистентности
        return await ChatManager.create_chat(participants, chat_type='private')

    @staticmethod
    async def get_chat_ids_by_user_id(user_id: int) -> List[int]:
        """Получить уникальные ID чатов для пользователя."""
        chats = await ChatManager.get_user_chats(user_id)
        return [chat.id for chat in chats]
