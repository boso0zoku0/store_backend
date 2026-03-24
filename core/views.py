from typing import Literal, Annotated

from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from core import db_helper
from products.crud import show_products

router = APIRouter(
    prefix="/products",
    tags=["Games"],
    # dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def get_products(session: AsyncSession = Depends(db_helper.get_session)):
    return await show_products(session)
