from hashlib import md5

from database.managers.user_manager import UserManager
from schemas.chat import ChatCreate

user_manager = UserManager()


def build_room_id_for_users(user1_id: int, user2_id: int) -> str:
    """Детерминированный room_id для пары пользователей.

    Независим от порядка (user1,user2) → сортируем и хешируем.
    """
    a, b = sorted([int(user1_id), int(user2_id)])
    return md5(f"{a}:{b}".encode()).hexdigest()


async def create_room_id(creator_id: int, companion_login: str) -> ChatCreate:
    companion_id = await user_manager.get_user_id_by_login(companion_login)
    room_id = build_room_id_for_users(creator_id, companion_id)
    return ChatCreate(room_id=room_id)
