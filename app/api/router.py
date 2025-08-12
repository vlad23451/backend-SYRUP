"""Главный роутер приложения.

Агрегирует и подключает все подроутеры (auth, user, followers, friends, history,
comment, like/dislike, message, websocket). 
Поддерживает чистую структуру и лёгкую масштабируемость API.
"""
from api.routers import *
from fastapi import APIRouter

main_router = APIRouter()

main_router.include_router(auth)
main_router.include_router(user)
main_router.include_router(followers)
main_router.include_router(friends)
main_router.include_router(history)
main_router.include_router(comment)
main_router.include_router(like)
main_router.include_router(dislike)
main_router.include_router(comment_like)
main_router.include_router(comment_dislike)
main_router.include_router(websocket)
main_router.include_router(message)
