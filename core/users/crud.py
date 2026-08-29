import os
from datetime import datetime, timezone
from typing import Annotated
import jwt
from fastapi import Depends, HTTPException, Form, Request, status
from pydantic import BaseModel, EmailStr, ValidationError
from sqlalchemy import select, func, update, text, JSON, cast
from sqlalchemy.exc import IntegrityError

from sqlalchemy.ext.asyncio import AsyncSession

from core import db_helper
from core.models import Users, Products, UsersProducts
from core.schemas.api import ApiStatus
from core.schemas.auth import UsersAdd, UserSchema, UsersGet
from core.schemas.users import UsersJwtDecode
from core.users.helper import hash_password, validate_password
from core.users.jwt import jwt_helper
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
import uuid

security = HTTPBearer()


async def get_current_auth_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    token = credentials.credentials
    try:
        payload = jwt_helper.decode(token)
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

        stmt = select(Users).where(Users.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
        return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_user_by_jwt_token(
    credentials: str,
) -> UsersJwtDecode:
    try:
        access_token = credentials.removeprefix("Bearer ")
        user = jwt_helper.decode(access_token)
        return user
    except Exception:
        raise HTTPException(
            detail="Invalid token", status_code=status.HTTP_401_UNAUTHORIZED
        )


async def get_user_by_cookie(
    session: AsyncSession, request: Request, is_logout: bool | None = False
):
    now = datetime.now(tz=timezone.utc)
    cookie = request.cookies.get("session_id")
    if not cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не авторизован",
        )
    stmt = select(Users).where(Users.cookie == cookie)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не авторизован",
        )
    if user.cookie_expires < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия истекла"
        )
    if is_logout:
        return user
    return {
        "username": user.name,
        "user_id": user.id,
        "url_id": user.url_id,
        "ip": user.ip,
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
        access = jwt_helper.encode(
            {
                "username": username,
                "user_id": user.id,
                "sub": username,
                "url_id": user.url_id,
            },
            token_type="access",
        )
        refresh = jwt_helper.encode(
            {
                "username": username,
                "user_id": user.id,
                "sub": username,
            },
            token_type="refresh",
        )
        await session.execute(
            update(Users)
            .where(Users.name == username)
            .values(
                cookie_expires=text("TIMEZONE('utc', now()) + interval '10800 minutes'")
            )
        )
        await session.commit()
        return {"access_token": access, "refresh_token": refresh, "user": user}

    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


async def get_me(
    request, session: AsyncSession = Depends(db_helper.session_dependency)
):
    user = await get_current_user(session, request)
    stmt = select(Users).where(Users.id == user["user_id"])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        return False
    return UsersGet(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        user_role=user.user_role,
        date_registration=user.date_registration,
        url_id=user.url_id,
    )


async def add_user(
    username: str,
    password: str,
    ip: str,
    session: AsyncSession = Depends(db_helper.session_dependency()),
):
    try:
        url_id = str(uuid.uuid4())
        stmt = select(Users).where(Users.name == username)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"type": "user exists"},
            )

        pwd = hash_password(password=password)
        user = Users(
            name=username,
            password=str(pwd),
            user_role="client",
            url_id=url_id,
            ip=ip,
        )
        session.add(user)
        access = jwt_helper.encode(
            payload={
                "username": username,
                "user_id": user.id,
                "sub": username,
                "url_id": url_id,
            },
            token_type="access",
        )
        refresh = jwt_helper.encode(
            payload={
                "username": username,
                "user_id": user.id,
                "sub": username,
            },
            token_type="refresh",
        )
        await session.commit()
        return UsersAdd(
            access_token=access,
            refresh_token=refresh,
            user=UserSchema.model_validate(user),
        )

    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "invalid username",
            },
        )
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "invalid email",
            },
        )


async def get_profile(session: AsyncSession, url_id: str):
    stmt = (
        select(
            Users.id,
            Users.name,
            Users.email,
            Users.phone,
            Users.date_registration,
            Users.photo,
            func.coalesce(func.count(UsersProducts.id), 0).label("total_orders"),
            func.coalesce(func.sum(Products.price), 0).label("total_price"),
            func.coalesce(
                func.json_agg(
                    func.json_build_object(
                        "id",
                        Products.id,
                        "short_name",
                        Products.short_name,
                        "status",
                        UsersProducts.status,
                        "created_at",
                        UsersProducts.created_at,
                        "price",
                        Products.price,
                        "photo",
                        Products.photos,
                        "quantity",
                        UsersProducts.quantity,
                    )
                ),
                # Expression: COALESCE(json_agg(...), '[]'::json)
                cast("[]", JSON),
            ).label("products_info"),
        )
        .select_from(Users)
        .outerjoin(UsersProducts, UsersProducts.users_id == Users.id)
        .outerjoin(Products, Products.id == UsersProducts.products_id)
        .where(Users.url_id == url_id)
        .group_by(Users.id)
    )

    result = await session.execute(stmt)
    row = result.mappings().first()

    return row


async def get_role_user(
    request: Request,
    session: AsyncSession,
):
    user = await get_user_by_cookie(session, request)
    stmt = select(Users.user_role).where(Users.id == user["user_id"])
    result = await session.execute(stmt)
    role = result.scalar_one_or_none()
    return role


async def add_photo_profile(
    request: Request,
    photo: str,
    session: AsyncSession,
):
    user = await get_user_by_cookie(session, request)
    stmt = update(Users).where(Users.id == user["user_id"]).values(photo=photo)
    await session.execute(stmt)
    await session.commit()
    return ApiStatus(status="success", message="Фото обновлено")
