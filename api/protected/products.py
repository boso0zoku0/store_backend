from typing import Annotated

from fastapi import Depends, APIRouter, UploadFile, File, Body
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from core import db_helper
from core.models.UsersProducts import ProductStatus
from core.schemas.products import ProductsPost
from core.users.crud import get_user_by_cookie, get_current_auth_user
from products.crud import (
    add_product,
    add_product_to_cart,
    change_product_status_to_cart,
    show_cart,
    remove_product_to_user,
)
from static.helper import upload_file

router = APIRouter(
    prefix="/products",
    tags=["Products"],
    dependencies=[Depends(get_current_auth_user)],
)


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
