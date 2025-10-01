from __future__ import annotations

from database.managers.like_manager import CommentDislikeManager
from database.managers.like_manager import CommentLikeManager
from database.managers.like_manager import DislikeManager
from database.managers.like_manager import LikeManager
from database.managers.user_manager import UserManager

from database.models.comment_like import CommentDislike
from database.models.comment_like import CommentLike
from database.models.history_like import HistoryDislike
from database.models.history_like import HistoryLike

from database.models.user import User

from schemas.like import CommentDislikeOut
from schemas.like import CommentLikeOut
from schemas.like import HistoryDislikeOut
from schemas.like import HistoryLikeOut
from schemas.user import UserShortOutWithFollowStatus

from services.cache_invalidation_service import CacheInvalidationService
from services.user_info_service import build_user_info
from services.score_service import ScoreService

class ReactionService:
    def __init__(self) -> None:
        self.like_manager = LikeManager()
        self.dislike_manager = DislikeManager()
        self.comment_like_manager = CommentLikeManager()
        self.comment_dislike_manager = CommentDislikeManager()
        self.user_manager = UserManager()

    async def build_comment_user_info(self, me_user_id: int, author_user_id: int) -> UserShortOutWithFollowStatus:
        user = await self.user_manager.get_obj_by_id(author_user_id)
        return await build_user_info(me_user_id=me_user_id, user=user)

    async def build_user_info(self, me_user_id: int, user: User) -> UserShortOutWithFollowStatus:
        return await build_user_info(me_user_id=me_user_id, user=user)

    async def _build_history_like_out(self, me_user_id: int, like_obj: HistoryLike) -> HistoryLikeOut:
        owner = await self.user_manager.get_obj_by_id(like_obj.user_id)
        user_info = await build_user_info(me_user_id=me_user_id, user=owner)
        return HistoryLikeOut.model_validate(
            {
                "id": like_obj.id,
                "user_id": like_obj.user_id,
                "history_id": like_obj.history_id,
                "created_at": like_obj.created_at,
                "user_info": user_info,
            }
        )

    async def _build_history_dislike_out(self, me_user_id: int, dislike_obj: HistoryDislike) -> HistoryDislikeOut:
        owner = await self.user_manager.get_obj_by_id(dislike_obj.user_id)
        user_info = await build_user_info(me_user_id=me_user_id, user=owner)
        return HistoryDislikeOut.model_validate(
            {
                "id": dislike_obj.id,
                "user_id": dislike_obj.user_id,
                "history_id": dislike_obj.history_id,
                "created_at": dislike_obj.created_at,
                "user_info": user_info,
            }
        )

    async def _build_comment_like_out(self, me_user_id: int, like_obj: CommentLike) -> CommentLikeOut:
        owner = await self.user_manager.get_obj_by_id(like_obj.user_id)
        user_info = await build_user_info(me_user_id=me_user_id, user=owner)
        return CommentLikeOut.model_validate(
            {
                "id": like_obj.id,
                "user_id": like_obj.user_id,
                "comment_id": like_obj.comment_id,
                "created_at": like_obj.created_at,
                "user_info": user_info,
            }
        )

    async def _build_comment_dislike_out(self, me_user_id: int, dislike_obj: CommentDislike) -> CommentDislikeOut:
        owner = await self.user_manager.get_obj_by_id(dislike_obj.user_id)
        user_info = await build_user_info(me_user_id=me_user_id, user=owner)
        return CommentDislikeOut.model_validate(
            {
                "id": dislike_obj.id,
                "user_id": dislike_obj.user_id,
                "comment_id": dislike_obj.comment_id,
                "created_at": dislike_obj.created_at,
                "user_info": user_info,
            }
        )

    # History reactions
    async def create_history_like(self, history_id: int, me: User) -> HistoryLikeOut:
        # Удаляем противоположную реакцию до создания текущей
        await self.dislike_manager.delete_by_user_and_target(user_id=me.id, target_id=history_id)
        existing = await self.like_manager.get_by_user_and_target(user_id=me.id, target_id=history_id)
        if existing is None:
            obj = HistoryLike(history_id=history_id, user_id=me.id)
            created = await self.like_manager.create_obj(obj)
            target = created
        else:
            target = existing
        await CacheInvalidationService.on_reaction_changed(history_id=history_id, me_user_id=me.id)
        await ScoreService.recompute_for_history_id(history_id)
        return await self._build_history_like_out(me_user_id=me.id, like_obj=target)

    async def get_history_like(self, history_id: int, me: User) -> HistoryLikeOut | None:
        existing = await self.like_manager.get_by_user_and_target(user_id=me.id, target_id=history_id)
        if existing is None:
            return None
        return await self._build_history_like_out(me_user_id=me.id, like_obj=existing)

    async def delete_history_like(self, history_id: int, me: User) -> None:
        await self.like_manager.delete_by_user_and_target(user_id=me.id, target_id=history_id)
        await CacheInvalidationService.on_reaction_changed(history_id=history_id, me_user_id=me.id)
        await ScoreService.recompute_for_history_id(history_id)

    async def create_history_dislike(self, history_id: int, me: User) -> HistoryDislikeOut:
        await self.like_manager.delete_by_user_and_target(user_id=me.id, target_id=history_id)
        existing = await self.dislike_manager.get_by_user_and_target(user_id=me.id, target_id=history_id)
        if existing is None:
            obj = HistoryDislike(history_id=history_id, user_id=me.id)
            created = await self.dislike_manager.create_obj(obj)
            target = created
        else:
            target = existing
        await CacheInvalidationService.on_reaction_changed(history_id=history_id, me_user_id=me.id)
        await ScoreService.recompute_for_history_id(history_id)
        return await self._build_history_dislike_out(me_user_id=me.id, dislike_obj=target)

    async def get_history_dislike(self, history_id: int, me: User) -> HistoryDislikeOut | None:
        existing = await self.dislike_manager.get_by_user_and_target(user_id=me.id, target_id=history_id)
        if existing is None:
            return None
        return await self._build_history_dislike_out(me_user_id=me.id, dislike_obj=existing)

    async def delete_history_dislike(self, history_id: int, me: User) -> None:
        await self.dislike_manager.delete_by_user_and_target(user_id=me.id, target_id=history_id)
        await CacheInvalidationService.on_reaction_changed(history_id=history_id, me_user_id=me.id)
        await ScoreService.recompute_for_history_id(history_id)

    # Comment reactions
    async def create_comment_like(self, comment_id: int, me: User) -> CommentLikeOut:
        await self.comment_dislike_manager.delete_by_user_and_target(user_id=me.id, target_id=comment_id)
        existing = await self.comment_like_manager.get_by_user_and_target(user_id=me.id, target_id=comment_id)
        if existing is None:
            obj = CommentLike(comment_id=comment_id, user_id=me.id)
            created = await self.comment_like_manager.create_obj(obj)
            target = created
        else:
            target = existing
        await CacheInvalidationService.on_reaction_changed(me_user_id=me.id)
        return await self._build_comment_like_out(me_user_id=me.id, like_obj=target)

    async def get_comment_like(self, comment_id: int, me: User) -> CommentLikeOut | None:
        existing = await self.comment_like_manager.get_by_user_and_target(user_id=me.id, target_id=comment_id)
        if existing is None:
            return None
        return await self._build_comment_like_out(me_user_id=me.id, like_obj=existing)

    async def delete_comment_like(self, comment_id: int, me: User) -> None:
        await self.comment_like_manager.delete_by_user_and_target(user_id=me.id, target_id=comment_id)
        await CacheInvalidationService.on_reaction_changed(me_user_id=me.id)

    async def create_comment_dislike(self, comment_id: int, me: User) -> CommentDislikeOut:
        await self.comment_like_manager.delete_by_user_and_target(user_id=me.id, target_id=comment_id)
        existing = await self.comment_dislike_manager.get_by_user_and_target(user_id=me.id, target_id=comment_id)
        if existing is None:
            obj = CommentDislike(comment_id=comment_id, user_id=me.id)
            created = await self.comment_dislike_manager.create_obj(obj)
            target = created
        else:
            target = existing
        await CacheInvalidationService.on_reaction_changed(me_user_id=me.id)
        return await self._build_comment_dislike_out(me_user_id=me.id, dislike_obj=target)

    async def get_comment_dislike(self, comment_id: int, me: User) -> CommentDislikeOut | None:
        existing = await self.comment_dislike_manager.get_by_user_and_target(user_id=me.id, target_id=comment_id)
        if existing is None:
            return None
        return await self._build_comment_dislike_out(me_user_id=me.id, dislike_obj=existing)

    async def delete_comment_dislike(self, comment_id: int, me: User) -> None:
        await self.comment_dislike_manager.delete_by_user_and_target(user_id=me.id, target_id=comment_id)
        await CacheInvalidationService.on_reaction_changed(me_user_id=me.id)
