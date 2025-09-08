from fastapi import APIRouter

from api.routers import *

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
main_router.include_router(role)
main_router.include_router(media)
