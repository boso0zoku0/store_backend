from datetime import datetime

from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    date_registration: datetime
    user_role: str
    url_id: str | None = None
    photo: str | None = None
    cookie: str | None = None
    ip: str | None = None
    cookie_expires: datetime | None = None


class UsersAdd(BaseModel):
    access_token: str
    refresh_token: str
    user: UserSchema


class UsersRegister(UsersAdd):
    cookie_session_id: str
    user_role: str
    ip: str


class UsersGet(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    user_role: str
    date_registration: datetime | None = None
    url_id: str | None = None
