from hashlib import md5

from database.managers.user_manager import UserManager
from schemas.chat import ChatCreate

user_manager = UserManager()

async def create_room_id(creator_id: int, companion_login: str) -> ChatCreate:
    companion_id = await user_manager.get_user_id_by_login(companion_login)
    room_id = md5((str(creator_id) + str(companion_id)).encode()).hexdigest()
    return ChatCreate(room_id=room_id)
