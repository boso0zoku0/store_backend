from datetime import datetime

from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    date_registration: datetime
    user_role: str | None = None
    url_id: str | None = None
    photo: str | None = None
    cookie: str | None = None
    ip: str | None = None

    # поле серверное (server_default) — оно не заполняется в Python, а только в БД.
    # При SELECT оно загружается, но SQLAlchemy не может его прочитать в асинхронном режиме без await
    # cookie_expires: datetime | None = None

    # разрешает создавать Pydantic-модели из SQLAlchemy-объектов
    class Config:
        from_attributes = True


class UsersAdd(BaseModel):
    access_token: str
    refresh_token: str
    user: UserSchema


class UsersRegister(BaseModel):
    access_token: str
    refresh_token: str
    user: UserSchema
    cookie_session_id: str
    user_role: str | None = None
    ip: str | None = None

    # разрешает создавать Pydantic-модели из SQLAlchemy-объектов
    class Config:
        from_attributes = True


class UsersGet(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    photo: str | None = None
    user_role: str
    date_registration: datetime | None = None
    url_id: str | None = None
