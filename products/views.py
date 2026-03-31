from typing import Literal, Annotated

import bcrypt
from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
    Response,
    UploadFile,
    File,
    Request,
    Body,
)
from pydantic import BaseModel
from redis.commands.search.reducers import count
from sqlalchemy.ext.asyncio import AsyncSession
from core import db_helper
from core.models import Products
from core.models.UsersProducts import ProductStatus
from products.crud import (
    show_products,
    add_product,
    add_product_to_cart,
    show_cart,
    show_product,
    remove_product_to_user,
    search_product,
    generate_slug,
    find_product_by_filters,
    change_product_status_to_cart,
)
from core.schemas.products import ProductsPost
from core.models.products import Filters
from static.helper import upload_file
from users.crud import get_user_by_cookie, get_current_user

router = APIRouter(
    prefix="/products",
    tags=["Games"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def get_products(session: AsyncSession = Depends(db_helper.session_dependency)):
    return await show_products(session)


@router.post("/upload")
async def upload_product(
    product: UploadFile = File(),
):
    return await upload_file(product)


@router.post("/")
async def create_products(
    product: ProductsPost,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await add_product(product, session)


@router.post("/add/to-cart")
async def create_product(
    slug: Annotated[str, Body()],
    product_status: Annotated[ProductStatus, Body()],
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):

    return await add_product_to_cart(
        slug=slug, product_status=product_status, request=request, session=session
    )


@router.post("/change/status")
async def change_product_status(
    slug: Annotated[str, Body()],
    stat: Annotated[ProductStatus, Body()],
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):

    return await change_product_status_to_cart(
        slug=slug,
        stat=stat,
        request=request,
        session=session,
    )


@router.get("/get/to-cart")
async def get_cart(
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):

    return await show_cart(request=request, session=session)


@router.delete("/delete")
async def delete_product(
    product_id: int,
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    user = await get_user_by_cookie(session, request)
    return await remove_product_to_user(
        user_id=user["user_id"], product_id=product_id, session=session
    )


@router.get("/get/product/")
async def get_product(
    slug: Annotated[str, Query()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):

    return await show_product(slug=slug, session=session)


# Api для поиска товара по названию. Не использую /get/product потому что юзер не будет
# По slug искать, будет по short_name
@router.post("/find")
async def find_product(
    short_name: Annotated[str, Query()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await search_product(short_name=short_name, session=session)


# Api для фильтрации товара, начинаю с цвета
@router.post("/filters/")
async def search_color(
    filters: Filters,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await find_product_by_filters(
        session=session,
        filters=filters,
    )
