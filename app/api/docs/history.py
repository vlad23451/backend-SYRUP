history_create_responses_raw = {
    "201": {
        "description": "История успешно создана.",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "title": "Заголовок",
                    "description": "Описание статьи",
                    "likes": 0,
                    "author": {"id": 2, "login": "author"},
                    "created_at": "2024-05-01T12:00:00",
                    "updated_at": None
                }
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
history_create_responses = {
    201: history_create_responses_raw["201"],
    422: history_create_responses_raw["422"],
    500: history_create_responses_raw["500"],
}

history_get_all_responses_raw = {
    "200": {
        "description": "Список всех историй.",
        "content": {
            "application/json": {
                "example": [
                    {
                        "id": 1,
                        "title": "Заголовок",
                        "description": "Описание статьи",
                        "likes": 5,
                        "author": {"id": 2, "login": "author"},
                        "created_at": "2024-05-01T12:00:00",
                        "updated_at": None
                    }
                ]
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
history_get_all_responses = {
    200: history_get_all_responses_raw["200"],
    500: history_get_all_responses_raw["500"],
}

history_get_responses_raw = {
    "200": {
        "description": "История найдена.",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "title": "Заголовок",
                    "description": "Описание статьи",
                    "likes": 5,
                    "author": {"id": 2, "login": "author"},
                    "created_at": "2024-05-01T12:00:00",
                    "updated_at": None
                }
            }
        }
    },
    "404": {
        "description": "История не найдена (HistoryNotFoundError)",
        "content": {
            "application/json": {
                "example": {"detail": "История не найдена."}
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
history_get_responses = {
    200: history_get_responses_raw["200"],
    404: history_get_responses_raw["404"],
    500: history_get_responses_raw["500"],
}

history_update_responses_raw = {
    "200": {
        "description": "История успешно обновлена.",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "title": "Обновлённый заголовок",
                    "description": "Обновлённое описание",
                    "likes": 5,
                    "author": {"id": 2, "login": "author"},
                    "created_at": "2024-05-01T12:00:00",
                    "updated_at": "2024-05-02T12:00:00"
                }
            }
        }
    },
    "404": {
        "description": "История не найдена (HistoryNotFoundError)",
        "content": {
            "application/json": {
                "example": {"detail": "История не найдена."}
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
history_update_responses = {
    200: history_update_responses_raw["200"],
    404: history_update_responses_raw["404"],
    500: history_update_responses_raw["500"],
}

history_delete_responses_raw = {
    "204": {
        "description": "История успешно удалена.",
        "content": {
            "application/json": {
                "example": None
            }
        }
    },
    "404": {
        "description": "История не найдена (HistoryNotFoundError)",
        "content": {
            "application/json": {
                "example": {"detail": "История не найдена."}
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
history_delete_responses = {
    204: history_delete_responses_raw["204"],
    404: history_delete_responses_raw["404"],
    500: history_delete_responses_raw["500"],
}

create_history_description = (
    "Создаёт новую историю (например, пост или событие) для текущего пользователя. "
    "Требует авторизации. "
    "Возвращает созданную историю. "
    "Возможные ошибки: объект не найден, ошибка прав, ошибка базы данных."
)

get_histories_description = (
    "Возвращает список всех историй с пагинацией (по страницам). "
    "Доступно без авторизации. "
    "Каждый элемент содержит информацию об истории и авторе. "
    "Возможные ошибки: ошибка базы данных."
)

get_history_description = (
    "Возвращает историю по её идентификатору. "
    "Требует авторизации. "
    "Возможные ошибки: история не найдена, ошибка прав, ошибка базы данных."
)

update_history_description = (
    "Изменяет историю по её идентификатору. "
    "Требует авторизации и права на изменение. "
    "Возвращает обновлённую историю. "
    "Возможные ошибки: история не найдена, ошибка прав, ошибка базы данных."
)

delete_history_description = (
    "Удаляет историю по её идентификатору. "
    "Требует авторизации и права на удаление. "
    "Возвращает статус 204 при успешном удалении. "
    "Возможные ошибки: история не найдена, ошибка прав, ошибка базы данных."
) 
