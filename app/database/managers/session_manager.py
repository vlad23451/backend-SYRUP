"""Singleton-менеджер async-сессий SQLAlchemy.

Предоставляет единообразный доступ к `AsyncSessionLocal` и `engine`.
Использование контекстного менеджера гарантирует корректное закрытие сессии.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Self

from database.config import AsyncSessionLocal, engine
from sqlalchemy.ext.asyncio import AsyncSession


class Manager:
    _instance = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self.AsyncSessionLocal = AsyncSessionLocal
        self.engine = engine

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, Any]:
        """Создать новую async-сессию и отдать вызывающему в контексте."""
        async with self.AsyncSessionLocal() as session:
                yield session
                
manager: Manager = Manager()
