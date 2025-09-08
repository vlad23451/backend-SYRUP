from typing import Dict, List

from schemas.user import UserShortOutWithFollowStatus
from services.user_info_service import build_user_info

async def build_user_list(rows, me_user_id):
    result = []
    if me_user_id is None:
        return result

    for user in rows.scalars().all():
        user_info = await build_user_info(me_user_id=me_user_id, user=user)
        result.append(user_info)
    return result

async def build_users_map(rows, me_user_id):
    if me_user_id is None:
        return {}
    
    users_map: Dict[int, List[UserShortOutWithFollowStatus]] = {}
    for hid, user in rows.all():
        user_info = await build_user_info(me_user_id, user)
        users_map.setdefault(hid, []).append(user_info)
    return users_map
