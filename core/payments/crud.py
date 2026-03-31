import enum
import json
from typing import Literal, cast
from unittest import removeResult

from fastapi import Depends, HTTPException, status, Request, UploadFile, File
from sqlalchemy import (
    select,
    asc,
    and_,
    func,
    desc,
    Integer,
    insert,
    update,
    union_all,
    delete,
    String,
    Boolean,
    or_,
    text,
)
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from core import db_helper
from core.models import (
    Users,
    Products,
    UsersProducts,
)
from core.schemas.products import ProductsPost
from core.schemas.users_products import UsersProductsBase
from users.crud import get_user_by_cookie


async def add_payment(request: Request, session: AsyncSession):
    user = get_user_by_cookie(session, request)
