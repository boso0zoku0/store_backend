from pydantic import BaseModel


class UsersBase(BaseModel):
    name: str


class UsersGet(UsersBase):
    id: int


class UsersPost(UsersBase):
    product_id: int
