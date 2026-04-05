import os
from datetime import datetime, timezone
from os import access
from typing import Annotated

from fastapi import Depends, HTTPException, Form, Request, status
from mypy.server.update import refresh_suppressed_submodules
from pydantic import BaseModel, EmailStr
from pydantic.v1 import ValidationError
from pydantic_core import PydanticCustomError
from sqlalchemy import select, func, update, text
from sqlalchemy.exc import IntegrityError

from sqlalchemy.ext.asyncio import AsyncSession

from core import db_helper
from core.models import Users, Products, UsersProducts
from core.models.UsersProducts import ProductStatus
from core.users.helper import hash_password, validate_password
from core.users.jwt import jwt_helper
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)

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
            raise HTTPException(401, "Invalid token")

        stmt = select(Users).where(Users.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(404, "User not found")
        return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


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
        access = jwt_helper.encode(
            {
                "username": username,
                "user_id": user.id,
                "sub": username,
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
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "user_role": user.user_role,
        "date_registration": user.date_registration,
    }


async def add_user(
    username: str,
    password: str,
    email: EmailStr,
    phone: str,
    session: AsyncSession = Depends(db_helper.session_dependency()),
):
    try:
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
            email=str(email),
            phone=phone,
            user_role=os.getenv("USER_ROLE"),
        )
        session.add(user)
        await session.commit()
        access = jwt_helper.encode(
            payload={
                "username": username,
                "user_id": user.id,
                "sub": username,
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
        return {"access_token": access, "refresh_token": refresh, "user": user}

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


class DataUser(BaseModel):
    name: str
    email: str
    phone: str
    product_short_name: str
    products_count: int
    products_price: int
    products_status: ProductStatus


async def get_profile(
    request: Request,
    session: AsyncSession,
):
    user = await get_user_by_cookie(session, request)
    stmt = (
        select(
            Users.id,
            Users.name,
            Users.email,
            Users.phone,
            Users.date_registration,
            func.count(UsersProducts.id).label("total_orders"),
            func.sum(Products.price).label("total_price"),
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
            ).label("products_info"),
        )
        .select_from(UsersProducts)
        .join(Users, Users.id == UsersProducts.users_id)
        .join(Products, Products.id == UsersProducts.products_id)
        .where(Users.id == user["user_id"])
        .group_by(Users.id, Users.name, Users.email, Users.phone)
    )

    result = await session.execute(stmt)
    row = result.mappings().first()
    print(row)

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
