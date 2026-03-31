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
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from core import db_helper
from core.models import Products
from core.payments.crud import add_payment
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
)
from core.schemas.products import ProductsPost
from core.models.products import Filters
from static.helper import upload_file
from users.crud import get_user_by_cookie

router = APIRouter(
    prefix="/payment",
    tags=["Payments"],
)


@router.post("/payment/create")
async def create_payment(
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await add_payment(
        request=request,
        session=session,
    )
