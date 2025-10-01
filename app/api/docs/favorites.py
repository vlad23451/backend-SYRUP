favorite_create_responses_raw = {
    "201": {
        "description": "История успешно добавлена в избранное.",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "user_id": 2,
                    "history_id": 3,
                    "created_at": "2024-05-01T12:00:00"
                }
            }
        }
    },
    "404": {
        "description": "История не найдена (HistoryNotFoundError)",
        "content": {
            "application/json": {
                "example": {"detail": "История не найдена"}
            }
        }
    },
    "409": {
        "description": "История уже добавлена в избранное (FavoriteAlreadyExistsError)",
        "content": {
            "application/json": {
                "example": {"detail": "История уже добавлена в избранное"}
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
favorite_create_responses = {
    201: favorite_create_responses_raw["201"],
    404: favorite_create_responses_raw["404"],
    409: favorite_create_responses_raw["409"],
    422: favorite_create_responses_raw["422"],
    500: favorite_create_responses_raw["500"],
}

favorite_delete_responses_raw = {
    "204": {
        "description": "История успешно удалена из избранного.",
        "content": {
            "application/json": {
                "example": None
            }
        }
    },
    "404": {
        "description": "История не найдена в избранном (FavoriteNotFoundError)",
        "content": {
            "application/json": {
                "example": {"detail": "История не найдена в избранном"}
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
favorite_delete_responses = {
    204: favorite_delete_responses_raw["204"],
    404: favorite_delete_responses_raw["404"],
    500: favorite_delete_responses_raw["500"],
}

favorite_get_responses_raw = {
    "200": {
        "description": "Список избранных историй получен.",
        "content": {
            "application/json": {
                "example": {
                    "history_ids": [123, 124, 125],
                    "histories": [
                        {
                            "id": 123,
                            "title": "Пример истории 1",
                            "description": "Описание истории 1",
                            "likes": 10,
                            "dislikes": 2,
                            "comments": 5,
                            "author": {
                                "id": 456,
                                "login": "author1",
                                "avatar_url": "https://example.com/avatar1.jpg"
                            },
                            "created_at": "2024-05-01T10:00:00",
                            "updated_at": None,
                            "liked_users": [],
                            "disliked_users": [],
                            "attached_files": []
                        },
                        {
                            "id": 124,
                            "title": "Пример истории 2",
                            "description": "Описание истории 2",
                            "likes": 15,
                            "dislikes": 1,
                            "comments": 8,
                            "author": {
                                "id": 457,
                                "login": "author2",
                                "avatar_url": "https://example.com/avatar2.jpg"
                            },
                            "created_at": "2024-05-01T09:00:00",
                            "updated_at": None,
                            "liked_users": [],
                            "disliked_users": [],
                            "attached_files": []
                        }
                    ],
                    "total": 3,
                    "skip": 0,
                    "limit": 10
                }
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
favorite_get_responses = {
    200: favorite_get_responses_raw["200"],
    500: favorite_get_responses_raw["500"],
}

favorite_check_responses_raw = {
    "200": {
        "description": "Статус избранного получен.",
        "content": {
            "application/json": {
                "example": {"is_favorite": True}
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
favorite_check_responses = {
    200: favorite_check_responses_raw["200"],
    500: favorite_check_responses_raw["500"],
}

create_favorite_description = (
    "Добавляет историю в избранное пользователя. "
    "Требует авторизации. "
    "Возвращает созданную запись избранного. "
    "Возможные ошибки: история не найдена, уже в избранном, ошибка базы данных."
)

get_favorites_description = (
    "Возвращает список избранных историй пользователя с пагинацией. "
    "Требует авторизации. "
    "Возвращает ID историй и полные данные историй с авторами, лайками и комментариями. "
    "Истории отсортированы по времени добавления в избранное (новые первые). "
    "Возможные ошибки: ошибка базы данных."
)

delete_favorite_description = (
    "Удаляет историю из избранного пользователя. "
    "Требует авторизации. "
    "Возвращает статус 204 при успешном удалении. "
    "Возможные ошибки: история не найдена в избранном, ошибка базы данных."
)

check_favorite_description = (
    "Проверяет, добавлена ли история в избранное пользователя. "
    "Требует авторизации. "
    "Возвращает булево значение статуса. "
    "Возможные ошибки: ошибка базы данных."
)
