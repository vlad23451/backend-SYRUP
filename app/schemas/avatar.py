from pydantic import BaseModel

class AvatarResponse(BaseModel):
    url: str

class UploadAvatarResponse(BaseModel):
    avatar_key: str
    url: str
