from database.managers.connection_singleton import get_connection_manager
from database.managers.message_manager import MessageManager
from database.managers.chat_manager import ChatManager
from services.validation_service import ValidationService as VS
from utils.json_utils import prepare_for_websocket
from core.logger import app_logger

message_manager = MessageManager()
connection_manager = get_connection_manager()

async def send_message_to_chat(message_data: dict,
                               from_me: bool = True) -> dict:
    VS.validate_required_fields(message_data, ["sender_id", "chat_id", "text"]) 
    VS.validate_string_length(str(message_data.get("text", "")), "text", min_length=1, max_length=2000)
    try:
        sender_id = int(message_data.get("sender_id"))
        chat_id = int(message_data.get("chat_id"))
    except Exception:
        raise ValueError("sender_id and chat_id must be integers")
    
    # Проверяем, что пользователь является участником чата
    if not await ChatManager.is_participant(chat_id, sender_id):
        raise ValueError(f"User {sender_id} is not a participant of chat {chat_id}")
    
    message_data = {
        **message_data, 
        "sender_id": sender_id,
        "chat_id": chat_id,
        "text": VS.sanitize_string(message_data["text"])
    }

    # Сохраняем в БД
    saved = await message_manager.save_message(message_data)

    # Обновляем время последней активности чата
    await ChatManager.update_chat_activity(chat_id)

    # Бродкастим сохранённую сущность всем участникам чата
    message_dict = saved.model_dump(mode='json')
    
    # Подготавливаем данные для WebSocket (используем chat_id как строку)
    websocket_message = prepare_for_websocket(message_dict)
    websocket_message["type"] = "new_message"  # Добавляем тип события
    
    # Отправляем всем участникам чата, подключенным к WebSocket
    await connection_manager.send_private_message(str(chat_id), websocket_message)
    
    # Получаем список участников чата для логирования после отправки
    chat_participants_ws = connection_manager.get_room_users(str(chat_id))
    app_logger.info(f"Сообщение разослано участникам чата {chat_id}: {message_dict.get('text', '')[:50]}...")
    app_logger.info(f"Участники чата {chat_id} подключенные к WebSocket после отправки: {chat_participants_ws}")

    return {**message_dict, "from_me": from_me}


async def edit_message(message_id: int, editor_user_id: int, new_text: str) -> dict:
    saved = await message_manager.edit_message(message_id, editor_user_id, new_text)
    payload = saved.model_dump(mode='json')
    payload["type"] = "message_edited"
    await connection_manager.send_private_message(str(saved.chat_id), payload)
    return payload


async def delete_message(message_id: int, requester_user_id: int, chat_id: int) -> dict:
    ok = await message_manager.delete_message(message_id, requester_user_id)
    payload = {"type": "message_deleted", "id": message_id, "chat_id": chat_id, "success": ok}
    await connection_manager.send_private_message(str(chat_id), payload)
    return payload


async def set_pinned(message_id: int, requester_user_id: int, is_pinned: bool, chat_id: int) -> dict:
    saved = await message_manager.set_pinned(message_id, requester_user_id, is_pinned)
    payload = saved.model_dump(mode='json')
    payload["type"] = "message_pinned"
    await connection_manager.send_private_message(str(saved.chat_id), payload)
    return payload
