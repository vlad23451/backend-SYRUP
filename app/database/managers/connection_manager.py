from typing import Dict, List

from api.dependencies.websocket import get_current_user
from core.logger import app_logger
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # user_id → WebSocket
        self.room_connections: Dict[str, List[str]] = {}    # room_id → [user_id1, user_id2]

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        app_logger.info(f"Попытка подключения WebSocket: {websocket.client}")
        
        try:
            data = await websocket.receive_json()
            if data.get("type") != "access_token":
                await websocket.send_json({"type": "error", "message": "Token required"})
                await websocket.close()
                return

            user = await get_current_user(data["token"])
            if not user:
                await websocket.send_json({"type": "error", "message": "Invalid token"})
                await websocket.close()
                app_logger.warning(f"WebSocket: невалидный токен при подключении: {data['token']}")
                return
            self.active_connections[user.id] = websocket
            app_logger.info(f"WebSocket: пользователь {user.id} успешно аутентифицирован и подключён")

            await websocket.send_json({"type": "success", "message": "Connection successful"}) 
        except Exception as e:
            app_logger.error(f"Ошибка при подключении WebSocket: {str(e)}")
            await websocket.send_json({"type": "error", "message": "Connection failed " + str(e)})
            await websocket.close()

    def disconnect_by_websocket(self, websocket: WebSocket):
        # Найти пользователя по объекту WebSocket и отключить
        for user_id, ws in list(self.active_connections.items()):
            if ws is websocket:
                self.disconnect(user_id)
                break

    async def join_room(self, room_id: str, user_id: str):
        if room_id not in self.room_connections:
            self.room_connections[room_id] = []
            app_logger.info(f"Создана новая комната room_id={room_id}")
        
        if user_id not in self.room_connections[room_id]:
            self.room_connections[room_id].append(user_id)
            app_logger.info(f"Пользователь {user_id} присоединился к комнате {room_id}")

    async def send_private_message(self, room_id: str, message: dict):
        if room_id in self.room_connections:
            for user_id in self.room_connections[room_id]:
                if user_id in self.active_connections:
                    try:
                        await self.active_connections[user_id].send_json(message)
                        app_logger.info(f"Отправлено сообщение пользователю {user_id} в комнате {room_id}: {message}")
                    except WebSocketDisconnect:
                        self.disconnect(user_id, room_id)
                        app_logger.warning(f"WebSocketDisconnect: пользователь {user_id} отключён из комнаты {room_id}")

    def disconnect(self, user_id: str, room_id: str = None):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            app_logger.info(f"Пользователь {user_id} отключён от WebSocket")
        
        if room_id and room_id in self.room_connections:
            if user_id in self.room_connections[room_id]:
                self.room_connections[room_id].remove(user_id)
                app_logger.info(f"Пользователь {user_id} удалён из комнаты {room_id}")
