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

websocket_router = APIRouter(prefix="/ws", tags=["Websocket"])
connection_manager = ConnectionManager()

@websocket_router.websocket("/",
                            name="WebSocket соединение")
async def websocket_connect(websocket: WebSocket):
    app_logger.info(f"WebSocket подключение: {websocket.client}")
    try:
        await connection_manager.connect(websocket)
        app_logger.info(f"WebSocket соединение установлено: {websocket.client}")
        
        while True:
            data = await websocket.receive_json()
            app_logger.info(f"WebSocket получил данные: {data}")
            print(data)
    except WebSocketDisconnect:
        connection_manager.disconnect_by_websocket(websocket)
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
                     summary='Отправить сообщение',
                     status_code=status.HTTP_200_OK,
                     description=send_message_description)
async def send_message(message_data: dict = Body(...),
                       user: User = Depends(get_current_user)) -> MessageOut:
    message = await send_message_to_room(message_data, message_data["room_id"])
    app_logger.info(f"WebSocket user_id={user.id} отправляет сообщение в room_id={message_data['room_id']}: {message}")
    await connection_manager.send_private_message(message_data["room_id"], message)
    return message
