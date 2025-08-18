"""Заполнение базы данных тестовыми данными.
    Создает:
    - N пользователей (по умолчанию: 1000)
    - Для каждого пользователя: 20-30 историй с рандомными created_at и некоторыми updated_at
    - Для каждой истории: рандомные likes, dislikes и comments с временными метками

    Запуск:
    python -m app.database.seed_data --users 1000 --min-h 20 --max-h 30 \
        --max-reactions 50 --max-comments 15
"""
from __future__ import annotations

import argparse
import asyncio
import os
import random
import string
import sys
from datetime import datetime, timedelta, timezone

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import bcrypt
from core.logger import app_logger
from database.init_db import init_db
from database.managers.session_manager import manager
from database.models.comments import Comment, CommentType
from database.models.history import History
from database.models.history_like import HistoryDislike, HistoryLike
from database.models.user import User
from sqlalchemy import select


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _random_text(prefix: str, min_len: int = 10, max_len: int = 30) -> str:
    length = random.randint(min_len, max_len)
    body = "".join(random.choices(string.ascii_letters + string.digits + " ", k=length))
    return f"{prefix} {body}".strip()


def _random_dt_within_days(days_back: int = 365) -> datetime:
    now = datetime.now(timezone.utc)
    seconds_back = random.randint(0, days_back * 24 * 3600)
    return now - timedelta(seconds=seconds_back)


async def _create_demo_users(session, count: int) -> list[User]:
    """Создать count пользователей с префиксом demo_user_ и вернуть созданные объекты."""
    result = await session.execute(select(User.login).where(User.login.like("demo_user_%")))
    existing_logins = {row[0] for row in result.all()}

    created: list[User] = []
    idx = 0
    while len(created) < count:
        login = f"demo_user_{idx}"
        idx += 1
        if login in existing_logins:
            continue
        user = User(
            login=login,
            password_hash=_hash_password("password"),
            role=1,
            avatar_key=None,
            about=None,
        )
        session.add(user)
        created.append(user)
        if len(created) % 200 == 0:
            await session.commit()
    await session.commit()
    return created


async def _ensure_seed_users_exist(session, num_users: int) -> list[int]:
    """Создает пользователей-инициаторов, если они не существуют, и возвращает их идентификаторы."""
    existing_ids: list[int] = []
    result = await session.execute(select(User.id).where(User.login.like("seed_user_%")))
    existing_ids = [row[0] for row in result.all()]

    to_create = num_users - len(existing_ids)
    if to_create <= 0:
        app_logger.info(f"Пользователи-инициаторы уже существуют: {len(existing_ids)}")
    else:
        app_logger.info(f"Создание {to_create} пользователей-инициаторов...")
        start_index = 0
        if existing_ids:
            start_index = len(existing_ids)

        created_count = 0
        for i in range(start_index, start_index + to_create):
            user = User(
                login=f"seed_user_{i}",
                password_hash=_hash_password("password"),
                role=1,
                avatar_key=None,
                about=None,
            )
            session.add(user)
            created_count += 1
            if created_count % 200 == 0:
                await session.commit()
        await session.commit()

        result = await session.execute(select(User.id).where(User.login.like("seed_user_%")))
        existing_ids = [row[0] for row in result.all()]

    return existing_ids


async def _create_histories_for_user(
    session,
    user_id: int,
    min_histories: int,
    max_histories: int,
) -> list[History]:
    num_histories = random.randint(min_histories, max_histories)
    histories: list[History] = []
    for _ in range(num_histories):
        created_at = _random_dt_within_days(365)
        histories.append(
            History(
                author_id=user_id,
                title=_random_text("Story", 8, 24),
                description=_random_text("", 40, 120),
                created_at=created_at,
                likes=0,
                dislikes=0,
                comments=0,
            )
        )
    session.add_all(histories)
    await session.commit()
    return histories


async def _add_reactions_and_comments(
    session,
    histories: list[History],
    all_user_ids: list[int],
    max_reactions_per_history: int,
    max_comments_per_history: int,
    updated_fraction: float = 0.3,
) -> None:
    """Добавляет реакции и комментарии к историям. Обновляет счетчики соответствующим образом.
    Также обновляет некоторые истории, чтобы установить updated_at.
    """
    # Preload existing like/dislike pairs for these histories to avoid duplicates
    history_ids = [h.id for h in histories]
    existing_like_pairs: set[tuple[int, int]] = set()
    existing_dislike_pairs: set[tuple[int, int]] = set()
    if history_ids:
        like_rows_existing = await session.execute(
            select(HistoryLike.user_id, HistoryLike.history_id).where(HistoryLike.history_id.in_(history_ids))
        )
        existing_like_pairs = set((uid, hid) for uid, hid in like_rows_existing.all())
        dislike_rows_existing = await session.execute(
            select(HistoryDislike.user_id, HistoryDislike.history_id).where(HistoryDislike.history_id.in_(history_ids))
        )
        existing_dislike_pairs = set((uid, hid) for uid, hid in dislike_rows_existing.all())

    for history in histories:
        total_reactions = random.randint(0, max_reactions_per_history)
        likes_count = random.randint(0, total_reactions)
        dislikes_count = total_reactions - likes_count

        candidate_users = [uid for uid in all_user_ids if uid != history.author_id]
        random.shuffle(candidate_users)

        like_user_ids = candidate_users[:likes_count]
        dislike_user_ids = candidate_users[likes_count : likes_count + dislikes_count]

        like_rows: list[HistoryLike] = []
        dislike_rows: list[HistoryDislike] = []
        # Track new pairs within this batch to keep them unique
        new_like_pairs: set[tuple[int, int]] = set()
        new_dislike_pairs: set[tuple[int, int]] = set()

        for uid in like_user_ids:
            pair = (uid, history.id)
            if pair in existing_like_pairs or pair in new_like_pairs:
                continue
            like_rows.append(
                HistoryLike(
                    user_id=uid,
                    history_id=history.id,
                    created_at=max(history.created_at, _random_dt_within_days(180)),
                )
            )
            new_like_pairs.add(pair)

        for uid in dislike_user_ids:
            pair = (uid, history.id)
            if pair in existing_dislike_pairs or pair in new_dislike_pairs:
                continue
            dislike_rows.append(
                HistoryDislike(
                    user_id=uid,
                    history_id=history.id,
                    created_at=max(history.created_at, _random_dt_within_days(180)),
                )
            )
            new_dislike_pairs.add(pair)

        comments_count = random.randint(0, max_comments_per_history)
        comment_rows: list[Comment] = []
        for _ in range(comments_count):
            commenter_id = random.choice(candidate_users) if candidate_users else history.author_id
            created_at = max(history.created_at, _random_dt_within_days(180))
            comment_rows.append(
                Comment(
                    user_id=commenter_id,
                    history_id=history.id,
                    content=_random_text("Comment", 20, 140),
                    comment_type=CommentType.TEXT.value,
                    created_at=created_at,
                )
            )

        history.likes = len(like_rows)
        history.dislikes = len(dislike_rows)
        history.comments = len(comment_rows)

        if like_rows:
            session.add_all(like_rows)
        if dislike_rows:
            session.add_all(dislike_rows)
        if comment_rows:
            session.add_all(comment_rows)

        if random.random() < updated_fraction:
            history.description = history.description + " (edited)"

    await session.commit()


async def seed_small_dataset(
    min_users: int = 40,
    max_users: int = 50,
    min_histories: int = 3,
    max_histories: int = 5,
) -> None:
    """Небольшой генератор: 40–50 пользователей, 3–5 историй на пользователя,
    с добавлением лайков/дизлайков и комментариев в небольших объёмах."""
    app_logger.info(
        "Старт малого заполнения: users=%s-%s, histories/user=%s-%s",
        min_users,
        max_users,
        min_histories,
        max_histories,
    )

    await init_db()

    async with manager.get_async_session() as session:
        target_users = random.randint(min_users, max_users)
        created_users = await _create_demo_users(session, target_users)
        user_ids = [u.id for u in created_users if isinstance(u.id, int)]

        for uid in user_ids:
            histories = await _create_histories_for_user(session, uid, min_histories, max_histories)
            # Добавляем немного реакций и комментариев для созданных историй
            await _add_reactions_and_comments(
                session=session,
                histories=histories,
                all_user_ids=user_ids,
                max_reactions_per_history=10,
                max_comments_per_history=5,
                updated_fraction=0.3,
            )

    app_logger.info("Малое заполнение завершено")


async def seed_data(
    num_users: int = 1000,
    min_histories: int = 20,
    max_histories: int = 30,
    max_reactions_per_history: int = 50,
    max_comments_per_history: int = 15,
) -> None:
    app_logger.info(
        "Начало заполнения базы данных тестовыми данными: users=%s, histories/user=%s-%s, max_reactions=%s, max_comments=%s",
        num_users,
        min_histories,
        max_histories,
        max_reactions_per_history,
        max_comments_per_history,
    )

    await init_db()

    async with manager.get_async_session() as session:
        user_ids = await _ensure_seed_users_exist(session, num_users)

    async with manager.get_async_session() as session:
        result = await session.execute(select(User.id).where(User.login.like("seed_user_%")))
        seed_user_ids = [row[0] for row in result.all()]

        processed = 0
        for uid in seed_user_ids:
            histories = await _create_histories_for_user(session, uid, min_histories, max_histories)
            await _add_reactions_and_comments(
                session,
                histories,
                seed_user_ids,
                max_reactions_per_history,
                max_comments_per_history,
            )
            processed += 1
            if processed % 50 == 0:
                app_logger.info("Заполнено историй для %s пользователей", processed)

    app_logger.info("Заполнение базы данных тестовыми данными завершено успешно")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Заполнение базы данных тестовыми данными")
    parser.add_argument("--small", action="store_true", help="Запустить малый генератор (40-50 пользователей, 3-5 историй)")
    parser.add_argument("--users", type=int, default=1000, help="Количество пользователей для создания")
    parser.add_argument("--min-h", type=int, default=20, help="Минимальное количество историй на пользователя")
    parser.add_argument("--max-h", type=int, default=30, help="Максимальное количество историй на пользователя")
    parser.add_argument(
        "--max-reactions",
        type=int,
        default=50,
        help="Максимальное количество реакций (лайков+дизлайков) на историю",
    )
    parser.add_argument(
        "--max-comments", type=int, default=15, help="Максимальное количество комментариев на историю"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.small:
        asyncio.run(
            seed_small_dataset(
                min_users=40,
                max_users=50,
                min_histories=3,
                max_histories=5,
            )
        )
    else:
        asyncio.run(
            seed_data(
                num_users=args.users,
                min_histories=args.min_h,
                max_histories=args.max_h,
                max_reactions_per_history=args.max_reactions,
                max_comments_per_history=args.max_comments,
            )
        )


