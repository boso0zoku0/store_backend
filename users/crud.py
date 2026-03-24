from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Form, Request, status, Response
from sqlalchemy import select, insert, and_, func, update, text
from sqlalchemy.exc import IntegrityError

from sqlalchemy.ext.asyncio import AsyncSession

from core import db_helper
from core.models import Users
from users.helper import hash_password, validate_password


async def get_user_by_cookie(
    session: AsyncSession, request: Request, is_logout: bool | None = False
):
    now = datetime.now(tz=timezone.utc)
    cookie = request.cookies.get("session_id")
    if not cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User unauthorized"
        )
    stmt = select(Users).where(Users.cookie == cookie)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User unauthorized"
        )
    if user.cookie_expires < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
        )
    if is_logout:
        return user
    return {
        "username": user.name,
        "user_id": user.id,
    }


async def get_current_user(
    session: Annotated[AsyncSession, Depends(db_helper.session_dependency)],
    request: Request,
):
    user_by_cookie = await get_user_by_cookie(session, request)

    return user_by_cookie


async def login(
    session: Annotated[AsyncSession, Depends(db_helper.session_dependency)],
    username: str = Form(),
    password: str = Form(),
):
    user = (await session.scalars(select(Users).where(Users.name == username))).first()

    if not user:
        return False
    hashed_pwd = hash_password(password)
    is_valid = validate_password(password=password, hashed_password=hashed_pwd)
    if is_valid:
        await session.execute(
            update(Users)
            .where(Users.name == username)
            .values(
                cookie_expires=text("TIMEZONE('utc', now()) + interval '10800 minutes'")
            )
        )
        await session.commit()
        return True

    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


async def get_user(
    username: str, session: AsyncSession = Depends(db_helper.session_dependency)
):
    stmt = select(Users.id).where(Users.name == username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        return False
    return True


async def add_user(
    username: str,
    password: str,
    session: AsyncSession = Depends(db_helper.session_dependency()),
):
    try:
        stmt = select(Users).where(Users.name == username)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user is already registered.",
            )
        pwd = hash_password(password=password)
        user = Users(name=username, password=str(pwd))
        session.add(user)
        await session.commit()

    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user is already registered. Change your registration details.",
        )
