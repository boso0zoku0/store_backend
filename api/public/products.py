from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from core import db_helper
from core.models.products import Filters
from products.crud import (
    show_products,
    show_product,
    search_product,
    find_product_by_filters,
)


router = APIRouter(
    tags=["Products"],
)


@router.get("/products")
async def get_products(session: AsyncSession = Depends(db_helper.session_dependency)):
    return await show_products(session)


@router.get("/product/get")
async def get_product(
    product_id: Annotated[int, Query()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):

    return await show_product(product_id=product_id, session=session)


@router.post("/product/find")
async def find_product(
    data: Annotated[str, Query()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await search_product(short_name=data, session=session)


@router.post("/products/filters/")
async def search_color(
    filters: Filters,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await find_product_by_filters(
        session=session,
        filters=filters,
    )
