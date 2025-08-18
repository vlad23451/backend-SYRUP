from typing import Dict, List, Set
import asyncio

from api.dependencies.websocket import get_current_user
from core.logger import app_logger
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {} # user_id → WebSocket
        self.room_connections: Dict[str, List[int]] = {} # room_id → [user_id]
        self.ws_to_user_id: Dict[WebSocket, int] = {} # WebSocket → user_id
        self.user_to_rooms: Dict[int, Set[str]] = {} # user_id → {room_id}
        self._lock = asyncio.Lock() # защита от гонок при модификациях

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
            async with self._lock:
                self.active_connections[user.id] = websocket
                self.ws_to_user_id[websocket] = user.id
                self.user_to_rooms.setdefault(user.id, set())
            app_logger.info(f"WebSocket: пользователь {user.id} успешно аутентифицирован и подключён")

            await websocket.send_json({"type": "success", "message": "Connection successful"}) 
        except Exception as e:
            app_logger.error(f"Ошибка при подключении WebSocket: {str(e)}")
            await websocket.send_json({"type": "error", "message": "Connection failed " + str(e)})
            await websocket.close()

    async def disconnect_by_websocket(self, websocket: WebSocket):
        async with self._lock:
            user_id = self.ws_to_user_id.pop(websocket, None)
        if user_id is not None:
            self.disconnect(user_id)

    def get_user_id(self, websocket: WebSocket) -> int | None:
        return self.ws_to_user_id.get(websocket)

    async def join_room(self, room_id: str, user_id: int):
        async with self._lock:
            if room_id not in self.room_connections:
                self.room_connections[room_id] = []
                app_logger.info(f"Создана новая комната room_id={room_id}")
            if user_id not in self.room_connections[room_id]:
                self.room_connections[room_id].append(user_id)
                self.user_to_rooms.setdefault(user_id, set()).add(room_id)
                app_logger.info(f"Пользователь {user_id} присоединился к комнате {room_id}")

    async def leave_room(self, room_id: str, user_id: int):
        async with self._lock:
            users = self.room_connections.get(room_id)
            if not users:
                return
            if user_id in users:
                users.remove(user_id)
                app_logger.info(f"Пользователь {user_id} покинул комнату {room_id}")
            if not users:
                self.room_connections.pop(room_id, None)
                app_logger.info(f"Комната {room_id} удалена (пустая)")
            if user_id in self.user_to_rooms:
                self.user_to_rooms[user_id].discard(room_id)
                if not self.user_to_rooms[user_id]:
                    self.user_to_rooms.pop(user_id, None)

    async def send_private_message(self, room_id: str, message: dict):
        users = list(self.room_connections.get(room_id, []))
        for user_id in users:
            ws = self.active_connections.get(user_id)
            if ws is not None:
                try:
                    await ws.send_json(message)
                except WebSocketDisconnect:
                    self.disconnect(user_id, room_id)
                except Exception as e:
                    app_logger.exception(f"Ошибка отправки сообщения пользователю {user_id} в комнате {room_id}: {e}")

    async def send_to_user(self, user_id: int, message: dict):
        ws = self.active_connections.get(user_id)
        if ws is None:
            return
        try:
            await ws.send_json(message)
        except WebSocketDisconnect:
            self.disconnect(user_id)
        except Exception as e:
            app_logger.exception(f"Ошибка отправки пользователю {user_id}: {e}")

    def disconnect(self, user_id: int, room_id: str | None = None):
        async def _do_disconnect():
            async with self._lock:
                ws = self.active_connections.pop(user_id, None)
                if ws is not None:
                    self.ws_to_user_id.pop(ws, None)
                    app_logger.info(f"Пользователь {user_id} отключён от WebSocket")

                if room_id is not None:
                    users = self.room_connections.get(room_id)
                    if users and user_id in users:
                        users.remove(user_id)
                        app_logger.info(f"Пользователь {user_id} удалён из комнаты {room_id}")
                        if not users:
                            self.room_connections.pop(room_id, None)
                    if user_id in self.user_to_rooms:
                        self.user_to_rooms[user_id].discard(room_id)
                        if not self.user_to_rooms[user_id]:
                            self.user_to_rooms.pop(user_id, None)
                else:
                    for rid in list(self.user_to_rooms.get(user_id, set())):
                        users = self.room_connections.get(rid)
                        if users and user_id in users:
                            users.remove(user_id)
                            app_logger.info(f"Пользователь {user_id} удалён из комнаты {rid}")
                            if not users:
                                self.room_connections.pop(rid, None)
                    self.user_to_rooms.pop(user_id, None)

        # schedule the coroutine since signature is sync
        asyncio.create_task(_do_disconnect())

    def is_connected(self, user_id: int) -> bool:
        return user_id in self.active_connections

    def get_user_rooms(self, user_id: int) -> List[str]:
        return list(self.user_to_rooms.get(user_id, set()))

    def get_room_users(self, room_id: str) -> List[int]:
        return list(self.room_connections.get(room_id, []))

    def is_user_in_room(self, room_id: str, user_id: int) -> bool:
        users = self.room_connections.get(room_id)
        return bool(users and user_id in users)

    async def ensure_room(self, room_id: str):
        async with self._lock:
            self.room_connections.setdefault(room_id, [])

    async def broadcast_room(self, room_id: str, message: dict, exclude_user_id: int | None = None):
        users = list(self.room_connections.get(room_id, []))
        for uid in users:
            if exclude_user_id is not None and uid == exclude_user_id:
                continue
            await self.send_to_user(uid, message)

    async def close_connection(self, user_id: int, code: int = 1000, reason: str | None = None):
        ws = self.active_connections.get(user_id)
        if ws is None:
            return
        try:
            await ws.close(code=code, reason=reason or "Closing")
        except Exception:
            pass
        finally:
            self.disconnect(user_id)
