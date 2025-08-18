from api.dependencies.auth import get_current_user
from api.docs.websocket import (create_private_chat_description,
                                send_message_description,
                                websocket_connect_description)
from core.logger import app_logger
from database.managers.connection_manager import ConnectionManager
from database.models.user import User
from fastapi import (APIRouter, Body, Depends, WebSocket, WebSocketDisconnect,
                     status)
from schemas.chat import ChatCreate
from schemas.message import MessageOut
from services.chat_service import create_room_id
from services.message_service import send_message_to_room
from services.chat_service import build_room_id_for_users
from database.managers.message_manager import MessageManager

websocket_router = APIRouter(prefix="/ws", tags=["Websocket"])
connection_manager = ConnectionManager()

@websocket_router.websocket("/",
                            name="WebSocket соединение")
async def websocket_connect(websocket: WebSocket):
    app_logger.info(f"WebSocket подключение: {websocket.client}")
    try:
        await connection_manager.connect(websocket)
        app_logger.info(f"WebSocket соединение установлено: {websocket.client}")
        
        message_manager = MessageManager()
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            app_logger.info(f"WebSocket event: {event_type} payload={data}")

            if event_type == "join_room":
                user_id = connection_manager.get_user_id(websocket)
                companion_id = int(data.get("companion_id"))
                if user_id is None or companion_id is None:
                    await websocket.send_json({"type": "error", "message": "join_room: invalid payload"})
                    continue
                room_id = build_room_id_for_users(int(user_id), int(companion_id))
                await connection_manager.join_room(room_id, int(user_id))
                await websocket.send_json({"type": "joined", "room_id": room_id})

            elif event_type == "leave_room":
                user_id = connection_manager.get_user_id(websocket)
                room_id = data.get("room_id")
                if user_id is None or not room_id:
                    await websocket.send_json({"type": "error", "message": "leave_room: invalid payload"})
                    continue
                await connection_manager.leave_room(room_id, int(user_id))
                await websocket.send_json({"type": "left", "room_id": room_id})

            elif event_type == "send_message":
                # ожидается: sender_id, receiver_id, text, request_id (опц.)
                request_id = data.get("request_id")
                try:
                    msg = {
                        "sender_id": int(data["sender_id"]),
                        "receiver_id": int(data["receiver_id"]),
                        "text": str(data["text"]),
                    }
                except Exception:
                    await websocket.send_json({"type": "error", "message": "send_message: invalid payload", "request_id": request_id})
                    continue
                # Разрешаем отправку даже если собеседник/комната не подключены: просто сохраняем и рассылаем присутствующим
                sent = await send_message_to_room(msg)
                await websocket.send_json({"type": "ack", "request_id": request_id, "message": sent})

            elif event_type == "typing":
                room_id = data.get("room_id")
                user_id = connection_manager.get_user_id(websocket)
                if not room_id or user_id is None:
                    continue
                await connection_manager.broadcast_room(room_id, {"type": "typing", "user_id": user_id}, exclude_user_id=user_id)

            elif event_type == "read_receipt":
                # ожидается: room_id, receiver_id, until_timestamp (опц.)
                room_id = data.get("room_id")
                receiver_id = data.get("receiver_id")
                until_ts = data.get("until_timestamp")
                if not room_id or receiver_id is None:
                    await websocket.send_json({"type": "error", "message": "read_receipt: invalid payload"})
                    continue
                updated = await message_manager.mark_read(room_id, int(receiver_id), until_ts)
                await connection_manager.broadcast_room(room_id, {
                    "type": "read_receipt",
                    "room_id": room_id,
                    "receiver_id": int(receiver_id),
                    "updated": updated,
                    "until_timestamp": until_ts,
                })

            else:
                await websocket.send_json({"type": "error", "message": "unknown event"})
    except WebSocketDisconnect:
        await connection_manager.disconnect_by_websocket(websocket)
        app_logger.info(f"WebSocket отключён: {websocket.client}")
    except Exception as e:
        app_logger.error(f"WebSocket ошибка: {str(e)}")
        try:
            await websocket.send_json({"error": str(e)})
        except RuntimeError:
            app_logger.warning("Попытка отправить сообщение после закрытия WebSocket")
            pass
        await websocket.close()

@websocket_router.post('/get_room_id',
                       summary='Получить room_id для чата',
                       status_code=status.HTTP_201_CREATED,
                       description=create_private_chat_description)
async def create_private_chat(companion_login: str = Body(..., embed=True),
                              user: User = Depends(get_current_user)) -> ChatCreate:
    return await create_room_id(user.id, companion_login)

@websocket_router.post('/send_message',
                     summary='Отправить сообщение (REST)',
                     status_code=status.HTTP_200_OK,
                     description=send_message_description)
async def send_message(message_data: dict = Body(...),
                       user: User = Depends(get_current_user)) -> MessageOut:
    message = await send_message_to_room(message_data)
    app_logger.info(f"REST user_id={user.id} отправляет сообщение в room_id={message.get('room_id')}: {message}")
    return message
