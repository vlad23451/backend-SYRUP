from fastapi import status

message_send_responses = {
    status.HTTP_201_CREATED: {
        "description": "Сообщение успешно отправлено.",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "sender_id": 2,
                    "room_id": "room_123",
                    "text": "Привет!",
                    "timestamp": "2024-05-01T12:00:00",
                    "from_me": True
                }
            }
        }
    },
    status.HTTP_404_NOT_FOUND: {
        "description": "Пользователь не найден (UserNotFoundError)",
        "content": {
            "application/json": {
                "example": {"detail": "Пользователь не найден."}
            }
        }
    },
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "description": "Ошибка валидации входных данных.",
        "content": {
            "application/json": {
                "example": {"detail": "Ошибка валидации."}
            }
        }
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Внутренняя ошибка сервера (DatabaseError)",
        "content": {
            "application/json": {
                "example": {"detail": "Внутренняя ошибка сервера."}
            }
        }
    },
}

get_chats_description = (
    "Возвращает список всех чатов текущего пользователя с последними сообщениями и информацией о собеседниках. "
    "Требует авторизации. "
    "Каждый элемент содержит данные о чате, последнем сообщении, собеседнике. "
    "Возможные ошибки: пользователь не найден, ошибка базы данных."
)

get_chats_responses_raw = {
    "200": {
        "description": "Список чатов пользователя.",
        "content": {
            "application/json": {
                "example": [
                    {
                        "chat_id": 123,
                        "companion_id": 42,
                        "companion_login": "user2",
                        "companion_avatar_url": "https://s3.example.com/avatars/example-companion.jpg?token=...",
                        "title": None,
                        "last_message": "Привет!",
                        "last_message_time": "2024-05-01T12:00:00",
                        "from_me": True,
                        "is_read": False
                    }
                ]
            }
        }
    },
    "404": {
        "description": "Пользователь не найден (UserNotFoundError)",
        "content": {
            "application/json": {
                "example": {"detail": "Пользователь не найден."}
            }
        }
    },
    "500": {
        "description": "Внутренняя ошибка сервера (DatabaseError)",
        "content": {
            "application/json": {
                "example": {"detail": "Внутренняя ошибка сервера."}
            }
        }
    },
}
get_chats_responses = {
    200: get_chats_responses_raw["200"],
    404: get_chats_responses_raw["404"],
    500: get_chats_responses_raw["500"],
}

search_messages_description = (
    "Поиск сообщений по тексту с возможностью фильтрации по чату, типу сообщения и дате. "
    "Требует авторизации. "
    "Возвращает найденные сообщения с контекстом и информацией о чатах. "
    "Поддерживает пагинацию и различные фильтры. "
    "Возможные ошибки: пустой запрос, доступ к чату запрещен, ошибка базы данных."
)

search_messages_responses_raw = {
    "200": {
        "description": "Результаты поиска сообщений.",
        "content": {
            "application/json": {
                "example": {
                    "results": [
                        {
                            "message": {
                                "id": 1,
                                "sender_id": 2,
                                "chat_id": 3,
                                "text": "Найденное сообщение с поисковым запросом",
                                "message_type": "text",
                                "timestamp": "2024-05-01T12:00:00",
                                "is_read": True,
                                "metadata": {},
                                "from_me": False,
                                "edited_at": None,
                                "is_deleted": False,
                                "is_pinned": False
                            },
                            "chat_title": "Групповой чат",
                            "companion_login": "user2",
                            "companion_avatar_url": "https://s3.example.com/avatars/user2.jpg",
                            "context_before": "Предыдущее сообщение...",
                            "context_after": "Следующее сообщение..."
                        }
                    ],
                    "total_count": 15,
                    "has_more": True,
                    "query": "поисковый запрос"
                }
            }
        }
    },
    "400": {
        "description": "Пустой поисковый запрос.",
        "content": {
            "application/json": {
                "example": {"detail": "Поисковый запрос не может быть пустым"}
            }
        }
    },
    "403": {
        "description": "Доступ к чату запрещен.",
        "content": {
            "application/json": {
                "example": {"detail": "Доступ к чату запрещен"}
            }
        }
    },
    "422": {
        "description": "Ошибка валидации входных данных.",
        "content": {
            "application/json": {
                "example": {"detail": "Ошибка валидации."}
            }
        }
    },
    "500": {
        "description": "Внутренняя ошибка сервера (DatabaseError)",
        "content": {
            "application/json": {
                "example": {"detail": "Внутренняя ошибка сервера."}
            }
        }
    },
}

search_messages_responses = {
    200: search_messages_responses_raw["200"],
    400: search_messages_responses_raw["400"],
    403: search_messages_responses_raw["403"],
    422: search_messages_responses_raw["422"],
    500: search_messages_responses_raw["500"],
}
