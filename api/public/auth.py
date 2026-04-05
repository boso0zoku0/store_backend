from os import access

from fastapi import Form, Depends, HTTPException, Body, APIRouter, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from core import db_helper
from core.models import Users
from core.users.crud import add_user, login
from core.users.helper import generate_session_id
from core.users.jwt import jwt_helper

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post("/registration", status_code=status.HTTP_201_CREATED)
async def register_user(
    response: Response,
    username: str = Form(),
    password: str = Form(),
    email: EmailStr = Form(),
    phone: str = Form(),
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    cookie = str(generate_session_id())
    response.set_cookie(key="session_id", value=cookie, max_age=604800, path="/")
    data = await add_user(
        session=session,
        username=username,
        password=password,
        email=email,
        phone=phone,
    )
    await session.execute(
        update(Users).where(Users.name == username).values(cookie=cookie)
    )
    await session.commit()
    return {
        "cookie_session_id": cookie,
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "user": data.get("user"),
        "user_role": "client",
    }


@router.post("/login", status_code=status.HTTP_200_OK)
async def user_login(
    response: Response,
    username: str = Form(),
    password: str = Form(),
    session: AsyncSession = Depends(db_helper.session_dependency),
):

    response_validate = await login(session, username, password)
    if response_validate:
        cookie_update = generate_session_id()
        response.set_cookie(
            key="session_id",
            value=cookie_update,
            max_age=604800,
            path="/",
            secure=True,
            domain=".cloudpub.ru",
        )
        await session.execute(
            update(Users)
            .where(Users.name == username)
            .values(
                cookie=cookie_update,
            )
        )
        await session.commit()
        return {
            "cookie_session_id": cookie_update,
            "access_token": response_validate.get("access_token"),
            "refresh_token": response_validate.get("refresh_token"),
            "user": response_validate.get("user"),
            "user_role": "client",
        }
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


class RefreshToken(BaseModel):
    refresh_token: str


@router.post("/refresh", status_code=status.HTTP_201_CREATED)
async def create_refresh_token(
    refresh_token: str = Body(),
):
    payload = jwt_helper.decode(refresh_token)
    if payload.get("type") != "refresh_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    access_token = jwt_helper.encode(
        payload={
            "username": payload["username"],
            "user_id": payload["user_id"],
            "sub": payload["username"],
        },
        token_type="access",
    )
    refresh_token = jwt_helper.encode(
        payload={
            "username": payload["username"],
            "user_id": payload["user_id"],
            "sub": payload["username"],
        },
        token_type="refresh",
    )
    return {"access_token": access_token, "refresh_token": refresh_token}
