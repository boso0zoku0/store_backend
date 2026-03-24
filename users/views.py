from fastapi import APIRouter, Depends, Response, Form, Request, status, HTTPException
from sqlalchemy import update, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from core import db_helper
from core.models import Users
from users.crud import add_user, login
from users.helper import generate_session_id

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post("/registration", status_code=status.HTTP_201_CREATED)
async def register_user(
    response: Response,
    username: str = Form(),
    password: str = Form(),
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    cookie = str(generate_session_id())
    response.set_cookie(key="session_id", value=cookie, max_age=604800, path="/")
    await add_user(session=session, username=username, password=password)
    await session.execute(
        update(Users).where(Users.name == username).values(cookie=cookie)
    )
    await session.commit()
    return {"username": username, "password": password, "cookie_session_id": cookie}


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
            domain=".cloudpub.ru",
            secure=True,
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
        }
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
