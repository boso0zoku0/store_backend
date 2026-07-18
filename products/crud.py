import json
from typing import cast

from fastapi import Request
from sqlalchemy import (
    select,
    and_,
    func,
    insert,
    update,
    Boolean,
)
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    Products,
    UsersProducts,
)
from core.models.UsersProducts import ProductStatus
from core.schemas.products import ProductsPost, ProductSearchResult, ProductFilterValues
from core.users.crud import get_user_by_cookie
import re
import unicodedata
from core.models.products import Filters
from core.websocket.notify.manager import manager as notify_manager
from products.helpers import get_product
from services.redis.config import redis_client


def generate_slug(name: str) -> str:
    # Приводим к латинице
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    # Заменяем пробелы и спецсимволы на дефис
    slug = re.sub(r"[^\w\s-]", "", name).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug


async def show_products(session: AsyncSession):
    cache_key = "products:all"
    cache = await redis_client.get(cache_key)
    if cache:
        return json.loads(cache)

    stmt = select(Products).order_by(Products.id)
    result = await session.execute(stmt)
    products = result.scalars().all()

    products_dict = [
        {
            "id": p.id,
            "name": p.name,
            "short_name": p.short_name,
            "price": p.price,
            "photos": p.photos,
            "description": p.description,
            "filters": p.filters,
            "about": p.about,
            "slug": p.slug,
        }
        for p in products
    ]

    await redis_client.set(
        cache_key,
        json.dumps(products_dict),
        ex=60,
    )
    return products_dict


async def show_product(
    product_id: int,
    session: AsyncSession,
):
    stmt = select(Products).where(Products.id == product_id)
    result = await session.execute(stmt)
    products = result.scalars().first()
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


async def remove_product_to_user(product_id: int, user_id: int, session: AsyncSession):
    stmt = select(UsersProducts).where(
        and_(
            UsersProducts.users_id == user_id,
            UsersProducts.products_id == product_id,
        )
    )
    res = await session.execute(stmt)
    product = res.scalar_one_or_none()
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

    await notify_manager.broadcast(
        username=user["username"],
        product_name=slug,
        url_id=user["url_id"],
    )
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


async def search_product(data: str, session: AsyncSession):

    query = data.strip().lower()
    limit = 0.5
    similarity = func.similarity(Products.short_name, query).label("similarity")
    if len(data) < 2:
        return await show_products(session)

    stmt = (
        select(Products, (similarity * 100).label("similarity_percent"))
        .where(Products.short_name.op("%")(query), similarity > limit)
        .order_by(similarity.desc())
    )
    result = await session.execute(stmt)
    products = result.mappings().all()
    if not products:
        return await show_products(session)
    return [
        ProductSearchResult(
            id=row["Products"].id,
            name=row["Products"].name,
            short_name=row["Products"].short_name,
            price=row["Products"].price,
            photos=row["Products"].photos,
            about=row["Products"].about,
            similarity_percent=row["similarity_percent"],
        )
        for row in products
    ]


# для отображения списка существующих фильтров
async def get_filters_names(session: AsyncSession):
    FILTER_LABELS = {
        "categories": "Тип",
        "price_range": "Ценовой диапазон",
        "colors": "Цвет",
        "volume": "Объем",
    }
    stmt = select(Products.filters).limit(1)
    result = await session.execute(stmt)
    filters = result.scalar()
    filters_name = list(filters.keys())
    show_filters = []
    for filter_name in filters_name:
        if filter_name in FILTER_LABELS.keys():
            show_filters.append(FILTER_LABELS[filter_name])
    return show_filters


# для отображения существующих значений для каждого фильтра
async def get_filters_values(session: AsyncSession):

    stmt = select(
        func.min(Products.price).label("min_price"),
        func.max(Products.price).label("max_price"),
        func.array_agg(func.distinct(Products.filters["categories"].astext)).label(
            "categories"
        ),
        func.array_agg(func.distinct(Products.filters["colors"])).label("colors"),
        func.array_agg(func.distinct(Products.filters["volume"][0].astext)).label(
            "volumes"
        ),
    )

    result = await session.execute(stmt)
    data = result.mappings().first()

    return ProductFilterValues(
        price_range={
            "min_price": data["min_price"] or 0,
            "max_price": data["max_price"] or 12000,
        },
        categories=data["categories"],
        colors=data["colors"],
        volumes=data["volumes"],
    )


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
            res = result.scalars().all()
            return res
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
