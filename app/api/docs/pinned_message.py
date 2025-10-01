from fastapi import status

pin_message_responses_raw = {
    "201": {
        "description": "Сообщение успешно закреплено.",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "message_id": 123,
                    "chat_id": 456,
                    "pinned_by_user_id": 789,
                    "pinned_at": "2024-01-15T10:30:00Z"
                }
            }
        }
    },
    "400": {
        "description": "Ошибка валидации или сообщение уже закреплено.",
        "content": {
            "application/json": {
                "example": {"detail": "Сообщение уже закреплено"}
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
        "description": "Внутренняя ошибка сервера.",
        "content": {
            "application/json": {
                "example": {"detail": "Внутренняя ошибка сервера."}
            }
        }
    },
}

pin_message_responses = {
    201: pin_message_responses_raw["201"],
    400: pin_message_responses_raw["400"],
    403: pin_message_responses_raw["403"],
    422: pin_message_responses_raw["422"],
    500: pin_message_responses_raw["500"],
}

unpin_message_responses_raw = {
    "200": {
        "description": "Сообщение успешно откреплено.",
        "content": {
            "application/json": {
                "example": {"message": "Сообщение успешно откреплено"}
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
    "404": {
        "description": "Закрепленное сообщение не найдено.",
        "content": {
            "application/json": {
                "example": {"detail": "Закрепленное сообщение не найдено"}
            }
        }
    },
    "500": {
        "description": "Внутренняя ошибка сервера.",
        "content": {
            "application/json": {
                "example": {"detail": "Внутренняя ошибка сервера."}
            }
        }
    },
}

unpin_message_responses = {
    200: unpin_message_responses_raw["200"],
    403: unpin_message_responses_raw["403"],
    404: unpin_message_responses_raw["404"],
    500: unpin_message_responses_raw["500"],
}

get_pinned_messages_responses_raw = {
    "200": {
        "description": "Список закрепленных сообщений чата.",
        "content": {
            "application/json": {
                "example": {
                    "pinned_messages": [
                        {
                            "id": 1,
                            "message": {
                                "id": 123,
                                "sender_id": 456,
                                "chat_id": 789,
                                "text": "Закрепленное сообщение",
                                "message_type": "text",
                                "timestamp": "2024-01-15T10:30:00Z",
                                "is_read": True,
                                "metadata": {},
                                "from_me": False,
                                "edited_at": None,
                                "is_deleted": False,
                                "is_pinned": False
                            },
                            "chat_title": "Рабочий чат",
                            "companion_login": "ivan_petrov",
                            "companion_avatar_url": "https://s3.example.com/avatars/ivan.jpg",
                            "pinned_by_user": {
                                "id": 789,
                                "login": "admin",
                                "avatar_url": "https://s3.example.com/avatars/admin.jpg",
                                "follow_status": "none"
                            },
                            "pinned_at": "2024-01-15T10:35:00Z"
                        }
                    ],
                    "total_count": 5,
                    "chat_id": 789
                }
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
    "500": {
        "description": "Внутренняя ошибка сервера.",
        "content": {
            "application/json": {
                "example": {"detail": "Внутренняя ошибка сервера."}
            }
        }
    },
}

get_pinned_messages_responses = {
    200: get_pinned_messages_responses_raw["200"],
    403: get_pinned_messages_responses_raw["403"],
    500: get_pinned_messages_responses_raw["500"],
}


pin_message_description = (
    "Закрепляет сообщение в чате. "
    "Требует авторизации и участия в чате. "
    "Одно сообщение может быть закреплено только один раз в чате. "
    "Возможные ошибки: сообщение не найдено, уже закреплено, доступ запрещен."
)

unpin_message_description = (
    "Открепляет сообщение в чате. "
    "Требует авторизации и участия в чате. "
    "Возможные ошибки: закрепленное сообщение не найдено, доступ запрещен."
)

get_pinned_messages_description = (
    "Возвращает список закрепленных сообщений чата с пагинацией. "
    "Требует авторизации и участия в чате. "
    "Сообщения отсортированы по времени закрепления (новые сверху). "
    "Возможные ошибки: доступ к чату запрещен."
)

