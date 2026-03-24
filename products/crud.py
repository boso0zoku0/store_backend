import enum
import json
from typing import Literal, cast

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
import re
import unicodedata


def generate_slug(name: str) -> str:
    # Приводим к латинице
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    # Заменяем пробелы и спецсимволы на дефис
    slug = re.sub(r"[^\w\s-]", "", name).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug


async def show_products(
    session: AsyncSession,
):
    stmt = select(Products).order_by(Products.id)
    result = await session.execute(stmt)
    products = result.scalars().all()
    return products


async def show_product(
    slug: str,
    session: AsyncSession,
):
    stmt = select(Products).where(Products.slug == slug)
    result = await session.execute(stmt)
    products = result.scalars().all()
    return products


async def add_product(
    product: ProductsPost,
    session: AsyncSession,
):
    slug = generate_slug(product.slug)
    product = Products(
        name=product.name,
        short_name=product.short_name,
        slug=slug,
        description=product.description.model_dump(),
        price=product.price,
        photos=product.photos,
        about=product.about,
    )
    session.add(product)
    await session.commit()


async def get_product(slug: str, session: AsyncSession):
    stmt = select(Products.id).where(Products.slug == slug)
    result = await session.execute(stmt)
    return result.scalars().first()


async def remove_product_to_user(product_id: int, user_id: int, session: AsyncSession):
    stmt = select(UsersProducts).where(
        and_(
            UsersProducts.users_id == user_id,
            UsersProducts.products_id == product_id,
        )
    )
    res = await session.execute(stmt)
    products = res.scalars().all()
    for product in products:
        await session.delete(product)
    await session.commit()


async def add_product_to_cart(
    slug: str,
    request: Request,
    session: AsyncSession,
):
    user = await get_user_by_cookie(session, request)
    product_id = await get_product(slug, session)
    stmt = insert(UsersProducts).values(
        users_id=user["user_id"],
        products_id=product_id,
    )
    await session.execute(stmt)
    await session.commit()


async def show_cart(
    request: Request,
    session: AsyncSession,
):
    user = await get_user_by_cookie(session, request)
    stmt = (
        select(Products, func.count(UsersProducts.quantity).label("quantity"))
        .join(UsersProducts, Products.id == UsersProducts.products_id)
        .where(
            UsersProducts.users_id == user["user_id"],
        )
        .group_by(Products.id)
    )
    result = await session.execute(stmt)
    return result.mappings().all()


async def search_product(short_name: str, session: AsyncSession):
    stmt = select(Products).where(Products.short_name == short_name)
    result = await session.execute(stmt)
    products = result.scalars().all()
    return products
