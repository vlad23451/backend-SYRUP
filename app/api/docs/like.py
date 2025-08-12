like_create_responses_raw = {
    "201": {
        "description": "Лайк успешно поставлен.",
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
    "409": {
        "description": "Лайк уже существует (LikeAlreadyExistsError)",
        "content": {
            "application/json": {
                "example": {"detail": "Лайк уже существует."}
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
like_create_responses = {
    201: like_create_responses_raw["201"],
    409: like_create_responses_raw["409"],
    422: like_create_responses_raw["422"],
    500: like_create_responses_raw["500"],
}

like_get_responses_raw = {
    "200": {
        "description": "Лайк найден.",
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
        "description": "Лайк не найден (LikeNotFoundError)",
        "content": {
            "application/json": {
                "example": {"detail": "Лайк не найден."}
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
like_get_responses = {
    200: like_get_responses_raw["200"],
    404: like_get_responses_raw["404"],
    500: like_get_responses_raw["500"],
}

like_delete_responses_raw = {
    "204": {
        "description": "Лайк успешно удалён.",
        "content": {
            "application/json": {
                "example": None
            }
        }
    },
    "404": {
        "description": "Лайк не найден (LikeNotFoundError)",
        "content": {
            "application/json": {
                "example": {"detail": "Лайк не найден."}
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
like_delete_responses = {
    204: like_delete_responses_raw["204"],
    404: like_delete_responses_raw["404"],
    500: like_delete_responses_raw["500"],
}

create_like_description = (
    "Создаёт лайк для объекта (например, истории). "
    "Требует авторизации. "
    "Возвращает созданный лайк. "
    "Возможные ошибки: объект не найден, ошибка прав, ошибка базы данных."
)

get_like_description = (
    "Возвращает лайк по его идентификатору. "
    "Требует авторизации. "
    "Возможные ошибки: лайк не найден, ошибка прав, ошибка базы данных."
)

delete_like_description = (
    "Удаляет лайк по его идентификатору. "
    "Требует авторизации и права на удаление. "
    "Возвращает статус 204 при успешном удалении. "
    "Возможные ошибки: лайк не найден, ошибка прав, ошибка базы данных."
) 
