from database.managers.followers_manager import FollowersManager
from database.managers.user_block_manager import UserBlockManager
from schemas.user import FollowStatus

followers_manager = FollowersManager()
user_block_manager = UserBlockManager()

async def check_follow_status(user_id: int, follower_id: int) -> FollowStatus:
    # user_id - пользователь, чей профиль смотрим
    # follower_id - текущий пользователь (кто смотрит)
    
    # Проверяем: заблокировал ли текущий пользователь (follower_id) того, чей профиль смотрим (user_id)
    is_user_blocked_by_me = await user_block_manager.is_user_blocked(blocker_id=follower_id, blocked_user_id=user_id)
    # Проверяем: заблокировал ли тот, чей профиль смотрим (user_id), текущего пользователя (follower_id)
    is_me_blocked_by_user = await user_block_manager.is_user_blocked(blocker_id=user_id, blocked_user_id=follower_id)
    
    if is_user_blocked_by_me:
        return FollowStatus.BLOCKED_BY_ME  # Я заблокировал этого пользователя
    elif is_me_blocked_by_user:
        return FollowStatus.BLOCKED_ME     # Этот пользователь заблокировал меня
    
    if user_id == follower_id:
        return FollowStatus.ME
    
    is_current_follows_them = await followers_manager.check_mutual_follow(
        target_id=follower_id,
        follower_id=user_id)

    is_they_follow_current = await followers_manager.check_mutual_follow(
        target_id=user_id,
        follower_id=follower_id)

    if is_current_follows_them and is_they_follow_current:
        follow_status = FollowStatus.MUTUAL
    elif is_they_follow_current:
        follow_status = FollowStatus.FOLLOWING_ME 
    elif is_current_follows_them:
        follow_status = FollowStatus.FOLLOWED_BY_ME
    else:
        follow_status = FollowStatus.NOT_FOLLOWING

    return follow_status


async def check_follow_status_many(user_id: int, follower_ids: list[int]) -> dict[int, FollowStatus]:
    result: dict[int, FollowStatus] = {}

    for target_id in follower_ids:
        if user_id == target_id:
            result[target_id] = FollowStatus.ME
            continue
            
        # user_id - текущий пользователь (кто смотрит)
        # target_id - пользователь, чей профиль смотрим
        
        # Проверяем: заблокировал ли текущий пользователь (user_id) того, чей профиль смотрим (target_id)
        is_target_blocked_by_me = await user_block_manager.is_user_blocked(blocker_id=user_id, blocked_user_id=target_id)
        # Проверяем: заблокировал ли тот, чей профиль смотрим (target_id), текущего пользователя (user_id)
        is_me_blocked_by_target = await user_block_manager.is_user_blocked(blocker_id=target_id, blocked_user_id=user_id)
        
        if is_target_blocked_by_me:
            result[target_id] = FollowStatus.BLOCKED_BY_ME  # Я заблокировал этого пользователя
        elif is_me_blocked_by_target:
            result[target_id] = FollowStatus.BLOCKED_ME     # Этот пользователь заблокировал меня
        else:
            result[target_id] = None 

    unblocked_ids = [tid for tid, status in result.items() if status is None]
    
    if unblocked_ids:
        my_following_rows = await followers_manager.get_following(user_id)
        my_following: set[int] = {row.user_id for row in my_following_rows}

        my_followers_rows = await followers_manager.get_followers(user_id)
        my_followers: set[int] = {row.follower_id for row in my_followers_rows}

        for target_id in unblocked_ids:
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
