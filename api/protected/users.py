from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request

from core import db_helper
from core.models import Users
from core.users.crud import get_current_auth_user, get_profile, get_me, get_role_user

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_auth_user)],
)


@router.get("/me", status_code=status.HTTP_201_CREATED)
async def get_user(
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_me(session=session, request=request)


@router.get("/get/{url_id}", status_code=status.HTTP_201_CREATED)
async def get_user(
    url_id: str,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_profile(url_id=url_id, session=session)


@router.get("/role", status_code=status.HTTP_201_CREATED)
async def get_role(
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_role_user(request=request, session=session)
