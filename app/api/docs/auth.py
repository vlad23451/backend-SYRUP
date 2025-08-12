from fastapi import status

auth_login_responses = {
    status.HTTP_200_OK: {
        "description": "Успешная аутентификация. Возвращает access и refresh токены.",
        "content": {
            "application/json": {
                "example": {
                    "access_token": "string",
                    "refresh_token": "string"
                }
            }
        }
    },
    status.HTTP_401_UNAUTHORIZED: {
        "description": "Неверные учетные данные (InvalidCredentialsError)",
        "content": {
            "application/json": {
                "example": {"detail": "Неверный логин или пароль."}
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

auth_register_responses = {
    status.HTTP_201_CREATED: {
        "description": "Пользователь успешно создан.",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "login": "user",
                    "about": None,
                    "avatar_url": None,
                    "role": 0
                }
            }
        }
    },
    status.HTTP_409_CONFLICT: {
        "description": "Пользователь с таким логином уже существует (UserAlreadyExistsError)",
        "content": {
            "application/json": {
                "example": {"detail": "Пользователь с таким логином уже существует."}
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

refresh_token_responses_raw = {
    "200": {
        "description": "Access токен успешно обновлён.",
        "content": {
            "application/json": {
                "example": {"message": "Access токен обновлен"}
            }
        }
    },
    "401": {
        "description": "Неавторизован (InvalidCredentialsError)",
        "content": {
            "application/json": {
                "example": {"detail": "Неавторизован."}
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
refresh_token_responses = {
    200: refresh_token_responses_raw["200"],
    401: refresh_token_responses_raw["401"],
    500: refresh_token_responses_raw["500"],
}

logout_responses_raw = {
    "204": {
        "description": "Успешный выход из аккаунта. Куки очищены.",
        "content": {
            "application/json": {
                "example": None
            }
        }
    },
    "401": {
        "description": "Неавторизован (InvalidCredentialsError)",
        "content": {
            "application/json": {
                "example": {"detail": "Неавторизован."}
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
logout_responses = {
    204: logout_responses_raw["204"],
    401: logout_responses_raw["401"],
    500: logout_responses_raw["500"],
}

create_user_description = (
    "Создаёт нового пользователя и выдаёт токены авторизации (access и refresh). "
    "Доступно без авторизации. "
    "Возвращает сообщение об успешной регистрации. "
    "Возможные ошибки: пользователь уже существует, ошибка базы данных."
)

login_description = (
    "Выполняет вход пользователя по логину и паролю. "
    "Доступно без авторизации. "
    "Устанавливает токены авторизации (access и refresh) в куки. "
    "Возвращает сообщение об успешном входе. "
    "Возможные ошибки: неверные учетные данные, ошибка базы данных."
)

refresh_access_token_description = (
    "Обновляет access токен по refresh токену. "
    "Требует валидный refresh токен. "
    "Возвращает новый access токен. "
    "Возможные ошибки: невалидный токен, ошибка базы данных."
)

logout_description = (
    "Выход из аккаунта. "
    "Очищает куки авторизации. "
    "Требует авторизации. "
    "Возвращает сообщение об успешном выходе."
) 
