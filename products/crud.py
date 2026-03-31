import enum
import json
from itertools import count
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
from core.models.UsersProducts import ProductStatus
from core.schemas.products import ProductsPost
from core.schemas.users_products import UsersProductsBase
from users.crud import get_user_by_cookie
import re
import unicodedata
from core.models.products import Filters


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
    product_status: ProductStatus,
    request: Request,
    session: AsyncSession,
):
    user = await get_user_by_cookie(session, request)
    product_id = await get_product(slug, session)
    stmt = insert(UsersProducts).values(
        users_id=user["user_id"],
        products_id=product_id,
        quantity=1,
        status=product_status.value,
    )
    await session.execute(stmt)
    await session.commit()


async def change_product_status_to_cart(
    slug: str,
    stat: ProductStatus,
    request: Request,
    session: AsyncSession,
):
    user = await get_user_by_cookie(session, request)
    product_id = await get_product(slug, session)
    stmt = (
        update(UsersProducts)
        .where(
            UsersProducts.users_id == user["user_id"],
            UsersProducts.products_id == product_id,
        )
        .values(
            status=stat.value,
        )
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
            and_(
                UsersProducts.users_id == user["user_id"],
                UsersProducts.status != "cancelled",
            )
        )
        .group_by(Products.id)
    )
    result = await session.execute(stmt)
    return result.mappings().all()


async def search_product(short_name: str, session: AsyncSession):
    if len(short_name) < 2:
        return
    stmt = select(Products).where(
        Products.short_name.ilike(f"%{short_name}%"),
    )
    result = await session.execute(stmt)
    products = result.scalars().all()
    return products


async def find_product_by_filters(filters: Filters, session: AsyncSession):
    stmt = select(Products)
    print(f"Фильтры: {filters}")
    conditions = []
    optional = []
    if filters.categories and filters.categories[0]:
        print(f"Поиск по категории: {filters.categories}")
        conditions.append(
            Products.filters["categories"].contains([filters.categories[0]])
        )
        print("??")

        if filters.priceRange is not None:
            print("Поиск по ценовому диапазону")
            min_filter = filters.priceRange[0]
            max_filter = filters.priceRange[1]
            conditions.append(
                and_(
                    Products.price >= min_filter,
                    Products.price <= max_filter,
                )
            )
            if filters.inStock is True:
                print(f"Поиск по наличию внутри поиска по категории: {filters.inStock}")
                conditions.append(cast(Products.filters["inStock"], Boolean) == True)
            if filters.colors and filters.colors[0]:
                print(f"Поиск по цветам внутри поиска по категории: {filters.colors}")
                conditions.append(Products.filters["colors"].astext.in_(filters.colors))
            if filters.volume is not None:
                print(f"Поиск по обьему внутри поиска по категории: {filters.volume}")
                conditions.append(Products.filters["volume"] == filters.volume)
            stmt = stmt.where(and_(*conditions))
            result = await session.execute(stmt)
            print(f"УСЛОВИЯ: {conditions}")
            print(f"ВЫВОД: {result.scalars().all()}")
            return result.scalars().all()
    else:
        print(f"Второстепенный поиск")
        print(f"price: {filters.priceRange}")
        if filters.priceRange is not None:
            min_filter = filters.priceRange[0]
            max_filter = filters.priceRange[1]
            optional.append(
                and_(
                    Products.price >= min_filter,
                    Products.price <= max_filter,
                )
            )
        if filters.colors and filters.colors[0]:
            print(f"Второстепенный поиск по цвету: {filters.colors}")
            optional.append(Products.filters["colors"].contains(filters.colors))

        if filters.volume and filters.volume:
            print(f"Второстепенный поиск по обьему: {filters.volume}")
            optional.append(Products.filters["volume"] == filters.volume)
        stmt = stmt.where(and_(*optional))
        result = await session.execute(stmt)
        return result.scalars().all()
