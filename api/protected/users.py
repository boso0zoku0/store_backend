from typing import Annotated

from fastapi import APIRouter, Depends, Request, Body, status, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core import db_helper
from core.schemas.api import ApiStatus
from core.schemas.auth import UsersGet
from core.users.crud import (
    get_current_auth_user,
    get_profile,
    get_me,
    get_role_user,
    add_photo_profile,
)
from services.s3.s3_client import s3_client

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_auth_user)],
)


@router.get(
    "/me",
    status_code=status.HTTP_201_CREATED,
    response_model=UsersGet,
    description="Get user info",
)
async def get_user(
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_me(session=session, request=request)


@router.post(
    "/add_photo",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiStatus,
    description="Add a photo to the user profile",
)
async def create_photo_profile(
    request: Request,
    photo: Annotated[
        UploadFile,
        File(..., media_type="image/jpeg", description="Фото профиля (JPEG)"),
    ],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    upload_file = await s3_client.upload_avatar(file=photo)
    return await add_photo_profile(
        session=session,
        photo=upload_file.get("file_url"),
        request=request,
    )


@router.get(
    "/get/{url_id}",
    status_code=status.HTTP_201_CREATED,
    description="Get the user profile with products",
)
async def get_user(
    url_id: str,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_profile(url_id=url_id, session=session)


@router.get(
    "/role",
    status_code=status.HTTP_201_CREATED,
    response_model=str,
)
async def get_role(
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_role_user(request=request, session=session)
