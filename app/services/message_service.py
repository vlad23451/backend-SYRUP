from database.managers.connection_manager import ConnectionManager
from database.managers.message_manager import MessageManager
from services.chat_service import build_room_id_for_users
from services.validation_service import ValidationService as VS

message_manager = MessageManager()
connection_manager = ConnectionManager()


async def send_message_to_room(message_data: dict,
                               from_me: bool = True) -> dict:
    """Сохранить сообщение и разослать в комнату.

    Ожидаемые поля в message_data: sender_id, receiver_id, text, room_id (опционально).
    room_id валидируется/нормализуется исходя из пары участников.
    """
    # Валидации и нормализация
    VS.validate_required_fields(message_data, ["sender_id", "receiver_id", "text"]) 
    VS.validate_string_length(str(message_data.get("text", "")), "text", min_length=1, max_length=2000)
    try:
        sender_id = int(message_data.get("sender_id"))
        receiver_id = int(message_data.get("receiver_id"))
    except Exception:
        raise ValueError("sender_id/receiver_id must be integers")
    normalized_room_id = build_room_id_for_users(sender_id, receiver_id)
    message_data = {**message_data, "room_id": normalized_room_id, "text": VS.sanitize_string(message_data["text"])[:2000]}

    # Сохраняем в БД
    saved = await message_manager.save_message(message_data)

    # Бродкастим сохранённую сущность
    await connection_manager.send_private_message(normalized_room_id, saved.model_dump())

    # Возвращаем объединённый ответ (совместимо со старым API)
    return {**saved.model_dump(), "from_me": from_me}
