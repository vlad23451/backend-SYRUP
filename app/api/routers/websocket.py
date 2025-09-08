from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi import status

from api.dependencies.auth import get_current_user
from api.docs.websocket import create_private_chat_description
from api.docs.websocket import send_message_description

from core.logger import app_logger

from database.managers.connection_singleton import get_connection_manager
from database.models.user import User

from services.chat_service import get_chat_id_for_users
from services.message_service import send_message_to_chat
from services.websocket_event_service import WebSocketEventHandler

from schemas.message import MessageOut

websocket_router = APIRouter(prefix="/ws", tags=["Websocket"])
connection_manager = get_connection_manager()

@websocket_router.websocket("/",
                            name="WebSocket соединение")
async def websocket_connect(websocket: WebSocket):
    app_logger.info(f"WebSocket подключение: {websocket.client}")
    
    try:
        connected = await connection_manager.connect(websocket)
        if not connected:
            return
            
        app_logger.info(f"WebSocket соединение установлено: {websocket.client}")
        
        event_handler = WebSocketEventHandler()
        
        while True:
            data = await websocket.receive_json()
            await event_handler.process_event(websocket, data)
            
    except WebSocketDisconnect:
        await connection_manager.disconnect_by_websocket(websocket)
        app_logger.info(f"WebSocket отключён: {websocket.client}")
    except Exception as e:
        app_logger.error(f"WebSocket ошибка: {str(e)}")
        import traceback
        app_logger.error(f"WebSocket traceback: {traceback.format_exc()}")
        
        await connection_manager.disconnect_by_websocket(websocket)
        
        try:
            await websocket.send_json({"error": str(e)})
        except RuntimeError:
            app_logger.warning("Попытка отправить сообщение после закрытия WebSocket")
            pass
        try:
            await websocket.close()
        except RuntimeError:
            app_logger.warning("Попытка закрыть уже закрытый WebSocket")
            pass

async def _create_private_chat_logic(user_id: int, companion_id: int) -> dict:
    """Логика создания приватного чата"""
    chat_id = await get_chat_id_for_users(user_id, companion_id)
    await connection_manager.join_room(str(chat_id), user_id)
    return {"chat_id": chat_id}


@websocket_router.post('/get_chat_id',
                       summary='Получить chat_id для чата',
                       status_code=status.HTTP_201_CREATED,
                       description=create_private_chat_description)
async def create_private_chat(companion_id: int = Body(..., embed=True),
                              user: User = Depends(get_current_user)) -> dict:
    """Эндпоинт для создания приватного чата"""
    return await _create_private_chat_logic(user.id, companion_id)

async def _send_message_logic(message_data: dict, user_id: int) -> MessageOut:
    """Логика отправки сообщения через POST запрос"""
    message = await send_message_to_chat(message_data)
    app_logger.info(f"user_id={user_id} отправляет сообщение в chat_id={message.get('chat_id')}: {message}")
    return message


@websocket_router.post('/send_message',
                     summary='Отправить сообщение',
                     status_code=status.HTTP_200_OK,
                     description=send_message_description)
async def send_message(message_data: dict = Body(...),
                       user: User = Depends(get_current_user)) -> MessageOut:
    """Эндпоинт для отправки сообщения через POST запрос"""
    return await _send_message_logic(message_data, user.id)
