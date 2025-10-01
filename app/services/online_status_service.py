from datetime import datetime, timezone
from typing import Set, Dict, Any
from database.managers.user_manager import UserManager
from database.managers.followers_manager import FollowersManager
from database.managers.friends_manager import FriendsManager
from schemas.user import UpdateUser
from core.logger import app_logger

class OnlineStatusService:
    def __init__(self, connection_manager=None):
        self.user_manager = UserManager()
        self.followers_manager = FollowersManager()
        self.friends_manager = FriendsManager()
        self.online_users: Set[int] = set()
        self.connection_manager = connection_manager
    
    async def user_connected(self, user_id: int):
        """Пользователь подключился"""
        self.online_users.add(user_id)
        await self._update_last_seen(user_id)
        app_logger.info(f"Пользователь {user_id} теперь онлайн")
        await self._notify_contacts_about_status(user_id, True)
    
    async def user_disconnected(self, user_id: int):
        """Пользователь отключился"""
        self.online_users.discard(user_id)
        await self._update_last_seen(user_id)
        app_logger.info(f"Пользователь {user_id} теперь оффлайн")
        await self._notify_contacts_about_status(user_id, False)
    
    async def _update_last_seen(self, user_id: int):
        """Обновить время последней активности"""
        try:
            user = await self.user_manager.get_obj_by_id(user_id)
            if user:
                last_seen = datetime.now(timezone.utc)
                update_data = UpdateUser(last_seen=last_seen)
                await self.user_manager.update_obj(user_id, update_data)
        except Exception as e:
            app_logger.error(f"Ошибка обновления last_seen для пользователя {user_id}: {e}")
    
    async def _notify_contacts_about_status(self, user_id: int, is_online: bool):
        """Уведомить контакты об изменении статуса"""
        try:
            # Получаем всех, кто подписан на этого пользователя
            followers = await self.followers_manager.get_followers(user_id)
            follower_ids = [f.follower_id for f in followers]
            
            # Получаем друзей
            friends = await self.friends_manager.get_friends(user_id)
            friend_ids = [f.friend_id if f.friend_id != user_id else f.user_id for f in friends]
            
            # Объединяем списки
            contact_ids = list(set(follower_ids + friend_ids))
            app_logger.info(f"Найдено {len(contact_ids)} контактов для уведомления о статусе пользователя {user_id}: {contact_ids}")
            
            # Отправляем уведомления через WebSocket
            status_message = {
                "type": "user_status_changed",
                "user_id": user_id,
                "is_online": is_online,
                "last_seen": datetime.now(timezone.utc).isoformat() if not is_online else None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Используем переданный connection_manager или получаем глобальный
            if self.connection_manager is None:
                from database.managers.connection_manager import get_connection_manager
                connection_manager = get_connection_manager()
            else:
                connection_manager = self.connection_manager
            
            for contact_id in contact_ids:
                is_contact_connected = connection_manager.is_connected(contact_id)
                app_logger.info(f"Проверяем контакт {contact_id}: подключен={is_contact_connected}, активные соединения={list(connection_manager.active_connections.keys())}")
                
                if is_contact_connected:
                    app_logger.info(f"Отправляем уведомление о статусе пользователя {user_id} (онлайн: {is_online}) контакту {contact_id}")
                    await connection_manager.send_to_user(contact_id, status_message)
                else:
                    app_logger.info(f"Контакт {contact_id} не подключен, пропускаем уведомление о статусе пользователя {user_id}")
                    
        except Exception as e:
            app_logger.error(f"Ошибка уведомления контактов о статусе {user_id}: {e}")
    
    def is_user_online(self, user_id: int) -> bool:
        """Проверить, онлайн ли пользователь"""
        return user_id in self.online_users
    
    async def get_online_status(self, user_id: int) -> Dict[str, Any]:
        """Получить статус пользователя"""
        is_online = self.is_user_online(user_id)
        user = await self.user_manager.get_obj_by_id(user_id)
        
        return {
            "user_id": user_id,
            "is_online": is_online,
            "last_seen": user.last_seen.isoformat() if user and user.last_seen else None
        }
    
    async def get_multiple_online_status(self, user_ids: list[int]) -> list[Dict[str, Any]]:
        """Получить статусы нескольких пользователей"""
        results = []
        for user_id in user_ids:
            status = await self.get_online_status(user_id)
            results.append(status)
        return results
