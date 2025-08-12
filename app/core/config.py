"""Глобальная конфигурация приложения (настройки через env).

Секреты и переменные окружения читаются из `.env` (см. `model_config`).
"""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LOG_DIR: str = "logs"
    LOG_FILE: str = "app.log"

    app_name: str = "Syrup Chat API"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///app/database/database.db"

    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    jwt_access_cookie_name: str = "access_token"
    jwt_refresh_cookie_name: str = "refresh_token"

    cors_origins: List[str] = ["http://localhost:3000",
                              "http://127.0.0.1:3000"]

    host: str = "0.0.0.0"
    port: int = 8000
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "env_prefix": "",
        "extra": "ignore"
    }

settings = Settings()
