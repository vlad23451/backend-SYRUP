"""
Сервис для обработки WebSocket событий
"""
from typing import Dict, Any, Optional
from fastapi import WebSocket

from core.logger import app_logger
from database.managers.connection_singleton import get_connection_manager
from database.managers.message_manager import MessageManager
from database.managers.user_manager import UserManager
from services.chat_service import get_chat_id_for_users
from services.message_service import send_message_to_chat, edit_message, delete_message, set_pinned


class WebSocketEventHandler:
    """Класс для обработки различных типов WebSocket событий"""
    
    def __init__(self):
        self.connection_manager = get_connection_manager()
        self.message_manager = MessageManager()
        self.user_manager = UserManager()
    
    async def handle_join_chat(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Обработка события подключения к чату"""
        user_id = self.connection_manager.get_user_id(websocket)
        companion_id = data.get("companion_id")
        
        if user_id is None or companion_id is None:
            await websocket.send_json({
                "type": "error", 
                "message": "join_chat: invalid payload"
            })
            return
        
        try:
            companion_id = int(companion_id)
            chat_id = await get_chat_id_for_users(int(user_id), companion_id)

            await self.connection_manager.join_room(str(chat_id), int(user_id))

            chat_participants = self.connection_manager.get_room_users(str(chat_id))
            active_connections = list(self.connection_manager.active_connections.keys())
            
            app_logger.info(f"Пользователь {user_id} подключился к чату {chat_id}")
            app_logger.info(f"Текущие участники чата {chat_id}: {chat_participants}")
            app_logger.info(f"Активные WebSocket соединения: {active_connections}")
            
            await websocket.send_json({
                "type": "joined", 
                "chat_id": chat_id
            })
            
        except Exception as e:
            app_logger.error(f"Ошибка подключения к чату: {e}")
            await websocket.send_json({
                "type": "error", 
                "message": "join_chat: failed to join"
            })

    async def handle_leave_chat(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Обработка события покидания чата"""
        user_id = self.connection_manager.get_user_id(websocket)
        chat_id = data.get("chat_id")
        
        if user_id is None or not chat_id:
            await websocket.send_json({
                "type": "error", 
                "message": "leave_chat: invalid payload"
            })
            return
        
        await self.connection_manager.leave_room(str(chat_id), int(user_id))
        
        chat_participants = self.connection_manager.get_room_users(str(chat_id))
        app_logger.info(f"Пользователь {user_id} покинул чат {chat_id}")
        app_logger.info(f"Оставшиеся участники чата {chat_id}: {chat_participants}")
        
        await websocket.send_json({
            "type": "left", 
            "chat_id": chat_id
        })

    async def handle_send_message(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Обработка события отправки сообщения"""
        request_id = data.get("request_id")
        
        try:
            sender_id = int(data["sender_id"])
            chat_id = int(data["chat_id"])
            
            current_user_id = self.connection_manager.get_user_id(websocket)
            if current_user_id != sender_id:
                await websocket.send_json({
                    "type": "error", 
                    "message": "sender_id mismatch", 
                    "request_id": request_id
                })
                return
            
            await self.connection_manager.join_room(str(chat_id), sender_id)
            
            chat_participants = self.connection_manager.get_room_users(str(chat_id))
            app_logger.info(f"Отправка сообщения в чат {chat_id} от пользователя {sender_id}")
            app_logger.info(f"Участники чата {chat_id} получат сообщение: {chat_participants}")
            
            # Получаем логин отправителя
            sender_user = await self.user_manager.get_obj_by_id(sender_id)
            sender_login = sender_user.login
            
            msg = {
                "sender_id": sender_id,
                "chat_id": chat_id,
                "text": str(data["text"]),
                "sender_login": sender_login,
            }
            
            sent = await send_message_to_chat(msg)
            
            await websocket.send_json({
                "type": "ack", 
                "request_id": request_id, 
                "message": sent
            })
            
        except Exception as e:
            app_logger.error(f"Ошибка отправки сообщения через WebSocket: {e}")
            await websocket.send_json({
                "type": "error", 
                "message": "send_message: invalid payload", 
                "request_id": request_id
            })

    async def handle_typing(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Обработка события набора текста"""
        chat_id = data.get("chat_id")
        user_id = self.connection_manager.get_user_id(websocket)
        
        if not chat_id or user_id is None:
            return
            
        await self.connection_manager.broadcast_room(
            str(chat_id), 
            {
                "type": "typing", 
                "user_id": user_id, 
                "chat_id": chat_id
            }, 
            exclude_user_id=user_id
        )

    async def handle_mark_as_read(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Обработка события пометки сообщений как прочитанных"""
        chat_id = data.get("chat_id")
        user_id = data.get("user_id")
        until_ts = data.get("until_timestamp")

        if not chat_id or user_id is None:
            await websocket.send_json({
                "type": "error", 
                "message": "mark_as_read: invalid payload"
            })
            return
        
        updated = await self.message_manager.mark_read(int(chat_id), int(user_id), until_ts)
        await self.connection_manager.broadcast_room(str(chat_id), {
            "type": "mark_as_read",
            "chat_id": int(chat_id),
            "user_id": int(user_id),
            "updated": updated,
            "until_timestamp": until_ts,
        })

    async def handle_edit_message(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Обработка события редактирования сообщения"""
        request_id = data.get("request_id")
        
        try:
            message_id = int(data["message_id"])
            new_text = str(data["text"])
            
            current_user_id = self.connection_manager.get_user_id(websocket)
            if current_user_id is None:
                await websocket.send_json({
                    "type": "error", 
                    "message": "edit_message: user not authenticated", 
                    "request_id": request_id
                })
                return
            
            # Получаем сообщение для определения chat_id
            message = await self.message_manager.get_obj_by_id(message_id)
            if not message:
                await websocket.send_json({
                    "type": "error", 
                    "message": "edit_message: message not found", 
                    "request_id": request_id
                })
                return
            
            # Используем сервис с WebSocket уведомлениями
            result = await edit_message(message_id, current_user_id, new_text)
            
            await websocket.send_json({
                "type": "ack", 
                "request_id": request_id, 
                "message": result
            })
            
        except Exception as e:
            app_logger.error(f"Ошибка редактирования сообщения через WebSocket: {e}")
            await websocket.send_json({
                "type": "error", 
                "message": "edit_message: invalid payload", 
                "request_id": request_id
            })

    async def handle_delete_message(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Обработка события удаления сообщения"""
        request_id = data.get("request_id")
        
        try:
            message_id = int(data["message_id"])
            
            current_user_id = self.connection_manager.get_user_id(websocket)
            if current_user_id is None:
                await websocket.send_json({
                    "type": "error", 
                    "message": "delete_message: user not authenticated", 
                    "request_id": request_id
                })
                return
            
            # Получаем сообщение для определения chat_id
            message = await self.message_manager.get_obj_by_id(message_id)
            if not message:
                await websocket.send_json({
                    "type": "error", 
                    "message": "delete_message: message not found", 
                    "request_id": request_id
                })
                return
            
            # Используем сервис с WebSocket уведомлениями
            result = await delete_message(message_id, current_user_id, message.chat_id)
            
            await websocket.send_json({
                "type": "ack", 
                "request_id": request_id, 
                "message": result
            })
            
        except Exception as e:
            app_logger.error(f"Ошибка удаления сообщения через WebSocket: {e}")
            await websocket.send_json({
                "type": "error", 
                "message": "delete_message: invalid payload", 
                "request_id": request_id
            })

    async def handle_pin_message(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Обработка события закрепления сообщения"""
        request_id = data.get("request_id")
        
        try:
            message_id = int(data["message_id"])
            is_pinned = bool(data["is_pinned"])
            
            current_user_id = self.connection_manager.get_user_id(websocket)
            if current_user_id is None:
                await websocket.send_json({
                    "type": "error", 
                    "message": "pin_message: user not authenticated", 
                    "request_id": request_id
                })
                return
            
            # Получаем сообщение для определения chat_id
            message = await self.message_manager.get_obj_by_id(message_id)
            if not message:
                await websocket.send_json({
                    "type": "error", 
                    "message": "pin_message: message not found", 
                    "request_id": request_id
                })
                return
            
            # Используем сервис с WebSocket уведомлениями
            result = await set_pinned(message_id, current_user_id, is_pinned, message.chat_id)
            
            await websocket.send_json({
                "type": "ack", 
                "request_id": request_id, 
                "message": result
            })
            
        except Exception as e:
            app_logger.error(f"Ошибка закрепления сообщения через WebSocket: {e}")
            await websocket.send_json({
                "type": "error", 
                "message": "pin_message: invalid payload", 
                "request_id": request_id
            })

    async def handle_unknown_event(self, websocket: WebSocket, event_type: str) -> None:
        """Обработка неизвестного типа события"""
        app_logger.warning(f"Получен неизвестный тип события: {event_type}")
        await websocket.send_json({
            "type": "error", 
            "message": "unknown event"
        })

    async def process_event(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Основной метод для обработки событий WebSocket"""
        event_type = data.get("type")
        app_logger.info(f"WebSocket event: {event_type} payload={data}")

        # Маппинг типов событий на соответствующие обработчики
        event_handlers = {
            "join_chat": self.handle_join_chat,
            "leave_chat": self.handle_leave_chat,
            "send_message": self.handle_send_message,
            "typing": self.handle_typing,
            "mark_as_read": self.handle_mark_as_read,
            "edit_message": self.handle_edit_message,
            "delete_message": self.handle_delete_message,
            "pin_message": self.handle_pin_message,
        }

        if event_type in event_handlers:
            await event_handlers[event_type](websocket, data)
        else:
            await self.handle_unknown_event(websocket, event_type)
