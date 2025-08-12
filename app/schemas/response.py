from pydantic import BaseModel
from schemas.user import FollowStatus

class SuccessResponse(BaseModel):
    success: bool

class FollowResponse(BaseModel):
    follow_status: FollowStatus
