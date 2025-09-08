from database.managers.chat_manager import ChatManager
from schemas.chat import ChatCreate

async def create_or_get_private_chat(creator_id: int, companion_id: int) -> ChatCreate:
    await ChatManager.create_or_get_private_chat(creator_id, companion_id)
    return ChatCreate(
        participants=[creator_id, companion_id],
        chat_type='private',
        title=None
    )

async def get_chat_id_for_users(user1_id: int, user2_id: int) -> int:
    chat = await ChatManager.create_or_get_private_chat(user1_id, user2_id)
    return chat.id
