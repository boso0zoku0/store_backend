import logging
from typing import Annotated
from fastapi import (
    Depends,
    APIRouter,
    UploadFile,
    File,
    Body,
    Header,
    Path,
    Header,
    Request,
    Response,
    HTTPException,
)
from fastapi.params import Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from core import db_helper
from core.models.UsersProducts import ProductStatus
from core.schemas.api import ApiStatus
from core.schemas.products import ProductsPost, ProductCommentAdd, Product, ProductCart
from core.users.crud import (
    get_user_by_cookie,
    get_current_auth_user,
    get_user_by_jwt_token,
)
from products.crud import (
    add_product,
    add_product_to_cart,
    change_product_status_to_cart,
    show_cart,
    remove_product_to_user,
    product_comment_add,
    show_cart_short,
)
from static.helper import upload_file

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/products",
    tags=["Products"],
    dependencies=[Depends(get_current_auth_user)],
)


@router.post(
    "/upload",
    response_model=str,
)
async def upload_product(
    product: UploadFile = File(),
):
    return await upload_file(product)


@router.post(
    "/add",
    response_model=ApiStatus,
)
async def create_products(
    product: ProductsPost,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await add_product(product, session)


@router.post(
    "/add/to-cart",
    response_model=ApiStatus,
)
async def create_product(
    slug: Annotated[str, Body()],
    product_status: Annotated[ProductStatus, Body()],
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):

    return await add_product_to_cart(
        slug=slug, product_status=product_status, request=request, session=session
    )


@router.post(
    "/change/status",
    response_model=ApiStatus,
)
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


@router.get(
    "/get/to-cart",
    response_model=list[ProductCart],
    status_code=status.HTTP_200_OK,
)
async def get_cart(
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):

    return await show_cart(request=request, session=session)


@router.delete(
    "/delete/{product_id}",
    description="Удалить товар из корзины",
    response_model=ApiStatus,
    # 204 статус означает нет контента, а я возвращаю ApiStatus в случае успеха, значит 200
    status_code=status.HTTP_200_OK,
)
async def delete_product(
    product_id: int,
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    user = await get_user_by_cookie(session, request)
    return await remove_product_to_user(
        user_id=user["user_id"], product_id=product_id, session=session
    )


@router.get(
    "/order/get",
    description="Кнопка оплатить заказ -> редирект сюда",
    status_code=status.HTTP_200_OK,
    response_model=list[Product],
)
async def get_order(
    credentials: Annotated[str, Header(alias="Authorization")],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    user = await get_user_by_jwt_token(credentials)
    result = await show_cart_short(session=session, user=user)
    return result


@router.post(
    "/feedback/add_comment/{product_id}",
    description="Отзыв к продукту, если в заказе их несколько, пусть юзер выберет один",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiStatus,
)
async def create_comment(
    product_id: Annotated[int, Path()],
    comment: Annotated[ProductCommentAdd, Body()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await product_comment_add(
        session=session,
        product_id=product_id,
        feedback=comment,
    )
