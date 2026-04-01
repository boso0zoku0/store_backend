from fastapi import APIRouter, Depends, Response, Form, Request, status, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from core import db_helper
from core.models import Users
from core.users.crud import (
    add_user,
    login,
    get_profile,
    get_current_user,
    get_current_auth_user,
)
from core.users.helper import generate_session_id
from fastapi.security import (
    HTTPBearer,
)

router = APIRouter(
    prefix="/users",
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
        }
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@router.get("/get", status_code=status.HTTP_201_CREATED)
async def get_user(
    request: Request,
    current_user: Users = Depends(get_current_auth_user),
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_profile(request=request, session=session)
