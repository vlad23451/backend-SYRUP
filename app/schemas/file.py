from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict

class FileOut(BaseModel):
    id: int
    filename: str
    file_key: str
    file_type: str
    mime_type: str
    file_size: int
    folder: str
    description: str | None = None
    is_public: bool = False
    download_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FileCreate(BaseModel):
    filename: str
    file_key: str
    file_type: str
    mime_type: str
    file_size: int
    folder: str
    description: str | None = None
    is_public: bool = False

class FileUpdate(BaseModel):
    description: str | None= None
    is_public: bool | None = None
