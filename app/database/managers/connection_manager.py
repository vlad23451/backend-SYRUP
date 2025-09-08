import asyncio
import json
import traceback

from typing import Dict
from typing import List
from typing import Set

from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from sqlalchemy import select

from database.managers.session_manager import manager
from database.models.chat import Chat

from api.dependencies.websocket import get_current_user
from core.logger import app_logger

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {} # user_id → WebSocket
        self.room_connections: Dict[str, List[int]] = {} # chat_id (as string) → [user_id]
        self.ws_to_user_id: Dict[WebSocket, int] = {} # WebSocket → user_id
        self.user_to_rooms: Dict[int, Set[str]] = {} # user_id → {chat_id (as string)}
        self._lock = asyncio.Lock() # защита от гонок при модификациях
        
        # Отладочная информация
        import time
        self._created_at = time.time()
        app_logger.info(f"🔧 ConnectionManager создан в {self._created_at}")
        
        # Флаг для отслеживания загрузки данных из БД
        self._db_loaded = False

    async def load_chat_participants_from_db(self):
        """Загрузить всех участников чатов из БД при запуске приложения."""
        if self._db_loaded:
            app_logger.info("Участники чатов уже загружены из БД")
            return
            
        try:            
            async with manager.get_async_session() as session:
                # Получаем все чаты с участниками
                result = await session.execute(select(Chat))
                chats = result.scalars().all()
                
                loaded_chats = 0
                total_participants = 0
                
                async with self._lock:
                    for chat in chats:
                        try:
                            # Получаем участников чата
                            if isinstance(chat.participants, str):
                                
                                participants = json.loads(chat.participants)
                            else:
                                participants = chat.participants
                            
                            if participants:
                                chat_id_str = str(chat.id)
                                self.room_connections[chat_id_str] = participants.copy()
                                
                                # Обновляем user_to_rooms для каждого участника
                                for user_id in participants:
                                    if user_id not in self.user_to_rooms:
                                        self.user_to_rooms[user_id] = set()
                                    self.user_to_rooms[user_id].add(chat_id_str)
                                
                                loaded_chats += 1
                                total_participants += len(participants)
                                
                                app_logger.debug(f"Загружен чат {chat_id_str} с участниками: {participants}")
                                
                        except (TypeError, ValueError, json.JSONDecodeError) as e:
                            app_logger.warning(f"Ошибка обработки участников чата {chat.id}: {e}")
                            continue
                
                self._db_loaded = True
                app_logger.info(f"✅ Загружено {loaded_chats} чатов с {total_participants} участниками из БД")
                app_logger.info(f"Всего чатов в памяти: {len(self.room_connections)}")
                
        except Exception as e:
            app_logger.error(f"Ошибка загрузки участников чатов из БД: {e}")
            app_logger.error(traceback.format_exc())

    async def sync_chat_with_db(self, chat_id: int):
        """Синхронизировать участников конкретного чата с БД."""
        try:
            async with manager.get_async_session() as session:
                result = await session.execute(
                    select(Chat).where(Chat.id == chat_id)
                )
                chat = result.scalars().first()
                
                if chat:
                    if isinstance(chat.participants, str):
                        
                        participants = json.loads(chat.participants)
                    else:
                        participants = chat.participants
                    
                    chat_id_str = str(chat_id)
                    
                    async with self._lock:
                        # Обновляем участников чата
                        old_participants = self.room_connections.get(chat_id_str, [])
                        self.room_connections[chat_id_str] = participants.copy()
                        
                        # Обновляем user_to_rooms
                        # Удаляем старые связи
                        for old_user_id in old_participants:
                            if old_user_id in self.user_to_rooms:
                                self.user_to_rooms[old_user_id].discard(chat_id_str)
                                if not self.user_to_rooms[old_user_id]:
                                    self.user_to_rooms.pop(old_user_id)
                        
                        # Добавляем новые связи
                        for user_id in participants:
                            if user_id not in self.user_to_rooms:
                                self.user_to_rooms[user_id] = set()
                            self.user_to_rooms[user_id].add(chat_id_str)
                    
                    app_logger.info(f"Синхронизирован чат {chat_id}: {old_participants} → {participants}")
                    
        except Exception as e:
            app_logger.error(f"Ошибка синхронизации чата {chat_id} с БД: {e}")

    async def connect(self, websocket: WebSocket) -> bool:
        await websocket.accept()
        app_logger.info(f"Попытка подключения WebSocket: {websocket.client}")
        
        try:
            # Ждем токен, игнорируя прочие события ограниченное время
            TOKEN_WAIT_SECONDS = 10
            token: str | None = None
            first_error_sent = False
            deadline = asyncio.get_event_loop().time() + TOKEN_WAIT_SECONDS
            while token is None:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    await websocket.send_json({"type": "error", "message": "Token required"})
                    await websocket.close()
                    return False
                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=max(0.1, remaining))
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "error", "message": "Token required"})
                    await websocket.close()
                    return False

                if not isinstance(data, dict):
                    continue
                msg_type = data.get("type")
                if msg_type == "access_token" and data.get("token"):
                    token = str(data["token"])
                    break
                # Игнорируем любые сообщения до получения токена; один раз уведомляем клиента
                if not first_error_sent:
                    try:
                        await websocket.send_json({"type": "error", "message": "Token required"})
                    except Exception:
                        pass
                    first_error_sent = True

            user = await get_current_user(token)
            if not user:
                await websocket.send_json({"type": "error", "message": "Invalid token"})
                await websocket.close()
                app_logger.warning(f"WebSocket: невалидный токен при подключении: {data['token']}")
                return False
            async with self._lock:
                # Проверяем, не был ли пользователь уже подключен
                if user.id in self.active_connections:
                    app_logger.warning(f"Пользователь {user.id} уже был подключен, перезаписываем соединение")
                
                self.active_connections[user.id] = websocket
                self.ws_to_user_id[websocket] = user.id
                self.user_to_rooms.setdefault(user.id, set())
                
            app_logger.info(f"WebSocket: пользователь {user.id} успешно аутентифицирован и подключён")
            app_logger.info(f"Всего активных WebSocket соединений: {len(self.active_connections)} - {list(self.active_connections.keys())}")
            app_logger.info(f"Всего активных чатов: {len(self.room_connections)}")

            await websocket.send_json({"type": "success", "message": "Connection successful"}) 
            return True
        except Exception as e:
            app_logger.error(f"Ошибка при подключении WebSocket: {str(e)}")
            await websocket.send_json({"type": "error", "message": "Connection failed " + str(e)})
            await websocket.close()
            return False

    async def disconnect_by_websocket(self, websocket: WebSocket):
        async with self._lock:
            user_id = self.ws_to_user_id.pop(websocket, None)
        if user_id is not None:
            app_logger.warning(f"Отключение пользователя {user_id} по WebSocket disconnect")
            # Сохраняем членство пользователя в комнатах, чтобы после перезагрузки страницы он оставался в room_connections
            self.disconnect(user_id, None, keep_rooms=True)
        else:
            app_logger.warning("Попытка отключить WebSocket, но пользователь не найден")

    def get_user_id(self, websocket: WebSocket) -> int | None:
        return self.ws_to_user_id.get(websocket)

    async def join_room(self, room_id: str, user_id: int):
        """Присоединить пользователя к чату (только для WebSocket подключения)."""
        async with self._lock:
            if room_id not in self.room_connections:
                self.room_connections[room_id] = []
                app_logger.info(f"Создан новый чат chat_id={room_id} (не найден в БД)")
            
            if user_id not in self.room_connections[room_id]:
                self.room_connections[room_id].append(user_id)
                self.user_to_rooms.setdefault(user_id, set()).add(room_id)
                app_logger.info(f"Пользователь {user_id} присоединился к чату {room_id}")
                app_logger.info(f"Все участники чата {room_id}: {self.room_connections[room_id]}")
            else:
                app_logger.info(f"Пользователь {user_id} уже в чате {room_id} (из БД или WebSocket)")

    async def leave_room(self, room_id: str, user_id: int):
        async with self._lock:
            users = self.room_connections.get(room_id)
            if not users:
                return
            if user_id in users:
                users.remove(user_id)
                app_logger.info(f"Пользователь {user_id} покинул чат {room_id}")
            if not users:
                self.room_connections.pop(room_id, None)
                app_logger.info(f"Чат {room_id} удален (пустой)")
            if user_id in self.user_to_rooms:
                self.user_to_rooms[user_id].discard(room_id)
                if not self.user_to_rooms[user_id]:
                    self.user_to_rooms.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict) -> bool:
        """Отправить сообщение конкретному пользователю, если он подключен.

        Возвращает True при успешной отправке, иначе False. При разрыве соединения
        выполняет мягкое отключение пользователя, сохраняя его членство в комнатах.
        """
        ws = self.active_connections.get(user_id)
        if ws is None:
            app_logger.warning(
                f"Пользователь {user_id} отсутствует в active_connections, пропускаем отправку"
            )
            return False
        try:
            await ws.send_json(message)
            return True
        except WebSocketDisconnect:
            app_logger.warning(
                f"Пользователь {user_id} отключился во время отправки сообщения; сохраняем членство в комнатах"
            )
            # Сохраняем членство в комнатах, удаляем только ws-соединение
            self.disconnect(user_id, None, keep_rooms=True)
            return False
        except RuntimeError as e:
            # Может возникать при попытке отправить после закрытия
            app_logger.warning(
                f"RuntimeError при отправке пользователю {user_id}: {e}"
            )
            return False
        except Exception as e:
            app_logger.exception(
                f"Не удалось отправить сообщение пользователю {user_id}: {e}"
            )
            return False

    async def send_private_message(self, room_id: str, message: dict):
        users = list(self.room_connections.get(room_id, []))
        successful_sends = 0
        failed_sends = 0
        
        app_logger.info(f"Отправка сообщения в чат {room_id} для {len(users)} участников: {users}")
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: почему active_connections пустой?
        if not self.active_connections:
            app_logger.error("🚨 КРИТИЧЕСКАЯ ОШИБКА: active_connections пустой!")
            app_logger.error(f"ws_to_user_id содержит: {list(self.ws_to_user_id.values())}")
            app_logger.error(f"user_to_rooms содержит: {list(self.user_to_rooms.keys())}")
        
        app_logger.info(f"Активные WebSocket соединения: {list(self.active_connections.keys())}")
        
        for user_id in users:
            ws = self.active_connections.get(user_id)
            if ws is not None:
                try:
                    await ws.send_json(message)
                    successful_sends += 1
                except WebSocketDisconnect:
                    app_logger.warning(f"Пользователь {user_id} отключился во время отправки сообщения")
                    # Сохраняем членство пользователя в комнатах, обновляем только ws-соединение
                    self.disconnect(user_id, None, keep_rooms=True)
                    failed_sends += 1
                except Exception as e:
                    app_logger.exception(f"Ошибка отправки сообщения пользователю {user_id} в чате {room_id}: {e}")
                    failed_sends += 1
            else:
                app_logger.warning(f"Пользователь {user_id} не найден в активных соединениях, но остается в чате")
                failed_sends += 1
        
        app_logger.info(f"Результат отправки в чат {room_id}: успешно={successful_sends}, ошибок={failed_sends}")

    def disconnect(self, user_id: int, room_id: str | None = None, keep_rooms: bool = False):
        async def _do_disconnect():
            async with self._lock:
                ws = self.active_connections.pop(user_id, None)
                if ws is not None:
                    self.ws_to_user_id.pop(ws, None)
                    app_logger.warning(f"Пользователь {user_id} отключён от WebSocket. Причина: {room_id or 'общее отключение'}, keep_rooms={keep_rooms}")
                else:
                    app_logger.warning(f"Попытка отключить пользователя {user_id}, но он не был в active_connections")

                if room_id is not None and not keep_rooms:
                    users = self.room_connections.get(room_id)
                    if users and user_id in users:
                        users.remove(user_id)
                        app_logger.info(f"Пользователь {user_id} удален из чата {room_id}")
                        if not users:
                            self.room_connections.pop(room_id, None)
                    if user_id in self.user_to_rooms:
                        self.user_to_rooms[user_id].discard(room_id)
                        if not self.user_to_rooms[user_id]:
                            self.user_to_rooms.pop(user_id, None)
                elif room_id is None and keep_rooms:
                    app_logger.info(f"Членство пользователя {user_id} в комнатах сохранено: {list(self.user_to_rooms.get(user_id, set()))}")
                else:
                    for rid in list(self.user_to_rooms.get(user_id, set())):
                        users = self.room_connections.get(rid)
                        if users and user_id in users:
                            users.remove(user_id)
                            app_logger.info(f"Пользователь {user_id} удален из чата {rid}")
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
