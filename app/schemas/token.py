"""Схемы для работы с токенами."""

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """Ответ с access токеном для WebSocket."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer", 
                "expires_in": 900
            }
        }
    }
