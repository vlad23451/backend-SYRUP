"""Зависимости пагинации для эндпоинтов.

Предоставляет стандартные профили пагинации с валидацией FastAPI Query.
"""
from fastapi import Query


def get_small_pagination(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=10),
) -> tuple[int, int]:
    return skip, limit


def get_large_pagination(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> tuple[int, int]:
    return skip, limit


