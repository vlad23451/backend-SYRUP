from pydantic import BaseModel


class AuthorOut(BaseModel):
    id: int
    login: str

    class Config:
        from_attributes = True
