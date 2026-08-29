from pydantic import BaseModel


class UsersProfile(BaseModel):
    id: int
    name: str
    email: str | None = None


class UsersJwtDecode(BaseModel):
    user_id: int
    username: str
    sub: str
    url_id: str | None = None
