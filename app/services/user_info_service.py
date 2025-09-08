from __future__ import annotations

from typing import Dict
from typing import Iterable

from database.models.user import User
from schemas.user import UserShortOut
from schemas.user import UserShortOutWithFollowStatus
from services.cache_service import UserCacheService
from services.friend_service import check_follow_status
from services.friend_service import check_follow_status_many

async def build_user_info(me_user_id: int, user: User) -> UserShortOutWithFollowStatus:
    cached = await UserCacheService.get_user_info(user_id=user.id, me_user_id=me_user_id)
    if cached is not None:
        return cached

    data = UserShortOut.model_validate(user).model_dump()
    follow_status = await check_follow_status(user_id=user.id, follower_id=me_user_id)
    data["follow_status"] = follow_status
    result = UserShortOutWithFollowStatus.model_validate(data)
    await UserCacheService.set_user_info(user_id=user.id, me_user_id=me_user_id, user_info=result)
    return result

async def build_user_info_many(me_user_id: int, users: Iterable[User]) -> Dict[int, UserShortOutWithFollowStatus]:
    users_list = list(users)
    ids = [u.id for u in users_list]
    statuses = await check_follow_status_many(user_id=me_user_id, follower_ids=ids)

    result: Dict[int, UserShortOutWithFollowStatus] = {}
    for user in users_list:
        cached = await UserCacheService.get_user_info(user_id=user.id, me_user_id=me_user_id)
        if cached is not None:
            result[user.id] = cached
            continue
        data = UserShortOut.model_validate(user).model_dump()
        data["follow_status"] = statuses.get(user.id)
        validated = UserShortOutWithFollowStatus.model_validate(data)
        await UserCacheService.set_user_info(user_id=user.id, me_user_id=me_user_id, user_info=validated)
        result[user.id] = validated
    return result
