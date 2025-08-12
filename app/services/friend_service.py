from database.managers.followers_manager import FollowersManager
from schemas.user import FollowStatus

followers_manager = FollowersManager()

async def check_follow_status(user_id: int, follower_id: int) -> FollowStatus:
    # Проверяем: я подписан на подписчика?
    is_current_follows_them = await followers_manager.check_mutual_follow(
        target_id=follower_id,
        follower_id=user_id)

    # Проверяем: подписчик подписан на меня?
    is_they_follow_current = await followers_manager.check_mutual_follow(
        target_id=user_id,
        follower_id=follower_id)

    if is_current_follows_them and is_they_follow_current:
        follow_status = FollowStatus.MUTUAL
    elif is_they_follow_current:
        follow_status = FollowStatus.FOLLOWING_ME 
    elif is_current_follows_them:
        follow_status = FollowStatus.FOLLOWED_BY_ME
    elif user_id == follower_id:
        follow_status = FollowStatus.ME
    else:
        follow_status = FollowStatus.NOT_FOLLOWING

    return follow_status


async def check_follow_status_many(user_id: int, follower_ids: list[int]) -> dict[int, FollowStatus]:
    """Батч-проверка follow_status для набора пользователей относительно текущего пользователя.

    Возвращает словарь: user_id -> FollowStatus
    """
    # Кого я читаю (я подписан на них)
    my_following_rows = await followers_manager.get_following(user_id)
    my_following: set[int] = {row.user_id for row in my_following_rows}

    # Кто читает меня (они подписаны на меня)
    my_followers_rows = await followers_manager.get_followers(user_id)
    my_followers: set[int] = {row.follower_id for row in my_followers_rows}

    result: dict[int, FollowStatus] = {}
    for target_id in follower_ids:
        if user_id == target_id:
            result[target_id] = FollowStatus.ME
            continue
        i_follow = target_id in my_following
        they_follow = target_id in my_followers
        if i_follow and they_follow:
            result[target_id] = FollowStatus.MUTUAL
        elif they_follow:
            result[target_id] = FollowStatus.FOLLOWING_ME
        elif i_follow:
            result[target_id] = FollowStatus.FOLLOWED_BY_ME
        else:
            result[target_id] = FollowStatus.NOT_FOLLOWING
    return result
