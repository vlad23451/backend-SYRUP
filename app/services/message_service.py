from database.managers.connection_manager import ConnectionManager
from database.managers.message_manager import MessageManager

message_manager = MessageManager()
connection_manager = ConnectionManager()

async def send_message_to_room(message_data: dict,
                               room_id: str,
                               from_me: bool = True) -> dict:
    await connection_manager.send_private_message(message_data, room_id)
    await message_manager.save_message(message_data)
    return message_data | {"from_me": from_me}
