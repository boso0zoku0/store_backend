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
    show_price_range,
    get_filters_name,
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


@router.get("/product/find")
async def find_product(
    data: Annotated[str, Query()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    print(f"data: {data}")
    return await search_product(data=data, session=session)


@router.post("/products/filters/")
async def find_product(
    filters: Filters,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await find_product_by_filters(
        session=session,
        filters=filters,
    )


@router.get("/products/filters/get")
async def filters_get(
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_filters_name(
        session=session,
    )


@router.get("/products/filter/price-range")
async def get_price_range(
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await show_price_range(
        session=session,
    )
