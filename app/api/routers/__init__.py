"""Экспорт подроутеров API для удобного подключения в `app/api/router.py`."""
from .auth import auth_router as auth
from .comment import comment_router as comment
from .comment_dislike import comment_dislike_router as comment_dislike
from .comment_like import comment_like_router as comment_like
from .dislike import dislike_router as dislike
from .followers import followers_router as followers
from .friends import friends_router as friends
from .history import history_router as history
from .like import like_router as like
from .message import message_router as message
from .user import user_router as user
from .websocket import websocket_router as websocket
