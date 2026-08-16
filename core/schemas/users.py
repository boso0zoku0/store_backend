from pydantic import BaseModel


class UsersBase(BaseModel):
    name: str


class UsersGet(UsersBase):
    id: int


class UsersPost(UsersBase):
    product_id: int


class UsersJwtDecode(BaseModel):
    user_id: int
    username: str
    sub: str
    url_id: str | None = None
