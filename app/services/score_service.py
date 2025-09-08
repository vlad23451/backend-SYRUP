from __future__ import annotations

import asyncio
import sys
import os

from typing import List

from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy import func

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from core.logger import app_logger
from database.managers.session_manager import manager
from database.models.history import History
from database.models.history_like import HistoryLike
from database.models.history_like import HistoryDislike
from database.models.history_score import HistoryScore
from database.models.comments import Comment

from services.recomendations_service import compute_history_score
from services.cache_service import HistoryScoreCacheService

class ScoreService:
    @staticmethod
    async def recompute_for_history_id(history_id: int) -> None:
        async with manager.get_async_session() as session:
            history: History | None = (
                await session.execute(select(History).where(History.id == history_id))
            ).scalars().first()
            if history is None:
                return

            likes_cnt = (
                await session.execute(
                    select(func.count(HistoryLike.id)).where(HistoryLike.history_id == history_id)
                )
            ).scalar_one()

            dislikes_cnt = (
                await session.execute(
                    select(func.count(HistoryDislike.id)).where(HistoryDislike.history_id == history_id)
                )
                ).scalar_one()

            comments_cnt = (
                await session.execute(
                    select(func.count(Comment.id)).where(Comment.history_id == history_id)
                )
            ).scalar_one()

            score_value = compute_history_score(
                likes=int(likes_cnt or 0),
                dislikes=int(dislikes_cnt or 0),
                comments=int(comments_cnt or 0),
                created_at=history.created_at
            )

            existing: HistoryScore | None = (
                await session.execute(
                    select(HistoryScore).where(HistoryScore.history_id == history_id)
                )
            ).scalars().first()
            
            if existing is None:
                row = HistoryScore(history_id=history_id, score=float(score_value))
                session.add(row)
            else:
                existing.score = float(score_value)

            await session.commit()
            await HistoryScoreCacheService.set_score(history_id, float(score_value))

    @staticmethod
    async def recompute_for_all_histories(batch_size: int = 500) -> None:
        app_logger.info("ScoreService: начать пересчет всех историй")
        async with manager.get_async_session() as session:
            offset = 0
            while True:
                rows: List[History] = (
                    await session.execute(
                        select(History).order_by(desc(History.created_at)).offset(offset).limit(batch_size)
                    )
                ).scalars().all()

                if not rows:
                    break

                for h in rows:
                    likes_cnt = (
                        await session.execute(
                            select(func.count(HistoryLike.id)).where(HistoryLike.history_id == h.id)
                        )
                    ).scalar_one()

                    dislikes_cnt = (
                        await session.execute(
                            select(func.count(HistoryDislike.id)).where(HistoryDislike.history_id == h.id)
                        )
                    ).scalar_one()

                    comments_cnt = (
                        await session.execute(
                            select(func.count(Comment.id)).where(Comment.history_id == h.id)
                        )
                    ).scalar_one()

                    score_value = compute_history_score(
                        likes=int(likes_cnt or 0),
                        dislikes=int(dislikes_cnt or 0),
                        comments=int(comments_cnt or 0),
                        created_at=h.created_at
                    )

                    existing: HistoryScore | None = (
                        await session.execute(
                            select(HistoryScore).where(HistoryScore.history_id == h.id)
                        )
                    ).scalars().first()

                    if existing is None:
                        session.add(HistoryScore(history_id=h.id, score=float(score_value)))
                    else:
                        existing.score = float(score_value)
                await session.commit()

                for h in rows:
                    likes_cnt = (
                        await session.execute(
                            select(func.count(HistoryLike.id)).where(HistoryLike.history_id == h.id)
                        )
                    ).scalar_one()

                    dislikes_cnt = (
                        await session.execute(
                            select(func.count(HistoryDislike.id)).where(HistoryDislike.history_id == h.id)
                        )
                    ).scalar_one()

                    comments_cnt = (
                        await session.execute(
                            select(func.count(Comment.id)).where(Comment.history_id == h.id)
                        )
                    ).scalar_one()

                    score_value = compute_history_score(
                        likes=int(likes_cnt or 0),
                        dislikes=int(dislikes_cnt or 0),
                        comments=int(comments_cnt or 0),
                        created_at=h.created_at
                    )
                    await HistoryScoreCacheService.set_score(h.id, float(score_value))
                offset += batch_size
        app_logger.info("ScoreService: пересчет всех историй завершен")


async def periodic_recompute_task(sleep_seconds: int) -> None:
    app_logger.info("ScoreService: периодическая задача запущена, интервал %ss", sleep_seconds)
    try:
        while True:
            try:
                await ScoreService.recompute_for_all_histories()
            except Exception as e:
                app_logger.exception("ScoreService: периодическая задача пересчета ошибка: %s", e)
            await asyncio.sleep(max(5, int(sleep_seconds)))
    except asyncio.CancelledError:
        app_logger.info("ScoreService: периодическая задача пересчета остановлена")
        raise

if __name__ == "__main__":
    asyncio.run(ScoreService.recompute_for_all_histories())
