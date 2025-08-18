from fastapi import status

user_get_responses = {
    status.HTTP_200_OK: {
        "description": "Пользователь найден.",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "login": "user",
                    "about": "О себе",
                    "avatar_key": "avatars/example-avatar.jpg",
                    "role": 0
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
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Внутренняя ошибка сервера (DatabaseError)",
        "content": {
            "application/json": {
                "example": {"detail": "Внутренняя ошибка сервера."}
            }
        }
    },
}

user_update_responses = {
    status.HTTP_200_OK: {
        "description": "Пользователь успешно обновлён.",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "login": "user",
                    "about": "Обновлённое описание",
                    "avatar_key": "avatars/example-avatar2.jpg",
                    "role": 0
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
    status.HTTP_403_FORBIDDEN: {
        "description": "Нет прав на обновление пользователя (OwnershipError)",
        "content": {
            "application/json": {
                "example": {"detail": "Нет прав на выполнение операции."}
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

user_histories_responses_raw = {
    "200": {
        "description": "Список историй пользователя.",
        "content": {
            "application/json": {
                "example": [
                    {
                        "id": 1,
                        "title": "Заголовок",
                        "description": "Описание",
                        "likes": 5,
                        "created_at": "2024-05-01T12:00:00",
                        "updated_at": None
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

user_histories_responses = {
    200: user_histories_responses_raw["200"],
    404: user_histories_responses_raw["404"],
    500: user_histories_responses_raw["500"],
}

user_delete_responses_raw = {
    "204": {
        "description": "Пользователь успешно удалён.",
        "content": {
            "application/json": {
                "example": None
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

user_delete_responses = {
    204: user_delete_responses_raw["204"],
    404: user_delete_responses_raw["404"],
    500: user_delete_responses_raw["500"],
}

patch_me_description = (
    "Изменяет данные текущего пользователя (например, имя, email, аватар и т.д.). "
    "Требует авторизации. "
    "Возвращает обновлённые данные пользователя. "
    "Возможные ошибки: пользователь не найден, ошибка базы данных."
)

get_me_description = (
    "Возвращает данные о текущем пользователе. "
    "Требует авторизации. "
    "Возможные ошибки: пользователь не найден, ошибка базы данных."
)

get_histories_description = (
    "Возвращает список историй, созданных текущим пользователем. "
    "Можно указать параметры skip и limit для пагинации. "
    "Требует авторизации. "
    "Возможные ошибки: пользователь не найден, ошибка базы данных."
)

delete_user_description = (
    "Удаляет аккаунт текущего пользователя и очищает куки авторизации. "
    "Требует авторизации. "
    "Возвращает статус 204 при успешном удалении. "
    "Возможные ошибки: пользователь не найден, ошибка базы данных."
)

get_user_by_id_description = (
    "Возвращает данные о пользователе по его идентификатору. "
    "Доступно без авторизации. "
    "Возможные ошибки: пользователь не найден, ошибка базы данных."
)

get_histories_by_id_description = (
    "Возвращает все истории пользователя по его идентификатору. "
    "Доступно без авторизации. "
    "Возможные ошибки: пользователь не найден, ошибка базы данных."
) 
