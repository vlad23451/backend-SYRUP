from typing import Tuple

from fastapi import Query

def get_small_pagination(skip: int = Query(0, ge=0),
                         limit: int = Query(10, ge=1, le=10)) -> Tuple[int, int]:
    return skip, limit

def get_medium_pagination(skip: int = Query(0, ge=0),
                         limit: int = Query(50, ge=1, le=50)) -> Tuple[int, int]:
    return skip, limit

def get_large_pagination(skip: int = Query(0, ge=0),
                         limit: int = Query(100, ge=1, le=100)) -> Tuple[int, int]:
    return skip, limit
