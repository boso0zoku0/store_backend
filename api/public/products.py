from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core import db_helper
from core.models.products import Filters
from core.users.crud import get_current_auth_user
from products.crud import (
    show_products,
    show_product,
    search_product,
    find_product_by_filters,
)

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.get("/")
async def get_products(session: AsyncSession = Depends(db_helper.session_dependency)):
    return await show_products(session)


@router.get("/get/product/")
async def get_product(
    slug: Annotated[str, Query()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):

    return await show_product(slug=slug, session=session)


@router.post("/find")
async def find_product(
    short_name: Annotated[str, Query()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await search_product(short_name=short_name, session=session)


@router.post("/filters/")
async def search_color(
    filters: Filters,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await find_product_by_filters(
        session=session,
        filters=filters,
    )
