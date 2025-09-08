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

    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000", 
        "https://myprojectfrontend.loca.lt"
    ]
    
    cors_allow_origin_regex: str = r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}|.*\.loca\.lt|.*\.ngrok\.io|.*\.trycloudflare\.com)(:\d+)?(/.*)?$"

    host: str = "0.0.0.0"
    port: int = 8000
        
    redis_url: str = "redis://localhost:6379/0"

    # Score recompute interval (seconds)
    score_refresh_seconds: int = 300
    
    # S3 Storage settings
    s3_access_key_id: str = "f55abbf2689e48a7a5c0682250228bf5"
    s3_secret_access_key: str = "c9a013b509114a2ebcc429ee9cefce71"
    s3_bucket_name: str = "test-backet-syrup"
    s3_region: str = "ru-7"
    s3_endpoint_url: str  = "https://s3.ru-7.storage.selcloud.ru" 
    s3_use_ssl: bool = True
    # SSL verification for S3: set to False to skip, or specify CA bundle path
    s3_verify_ssl: bool = False
    s3_ca_bundle_path: str | None = None
    
    # File upload settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: list[str] = [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "video/mp4", "video/webm", "video/ogg",
        "audio/mpeg", "audio/wav", "audio/ogg",
        "application/pdf", "text/plain"
    ]
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "env_prefix": "",
        "extra": "ignore"
    }

settings = Settings()
