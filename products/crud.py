import json

from fastapi import Request, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, and_, func, insert, update, Boolean, or_, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from broker.config import exchange
from core.models import (
    Products,
    UsersProducts,
    ProductsFeedback,
    Users,
)
from core.models.UsersProducts import ProductStatus
from core.schemas.api import ApiStatus

from core.schemas.products import (
    ProductsPost,
    ProductSearchResult,
    FiltersValues,
    FiltersFind,
    ProductCommentAdd,
    GetProductReviewers,
    Filters,
)
from core.schemas.users import UsersJwtDecode
from core.users.crud import get_user_by_cookie
import re
import unicodedata
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
    return ApiStatus(status="success", message="Продукт создан")


async def remove_product_to_user(product_id: int, user_id: int, session: AsyncSession):
    stmt = select(UsersProducts).where(
        and_(
            UsersProducts.users_id == user_id,
            UsersProducts.products_id == product_id,
        )
    )
    res = await session.execute(stmt)
    product = res.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Продукта нету в корзине"
        )
    await session.delete(product)
    await session.commit()
    return ApiStatus(status="success", message="Товар удален из корзины")


async def add_product_to_cart(
    slug: str,
    product_status: ProductStatus,
    request: Request,
    session: AsyncSession,
):
    product_id = await get_product(slug, session)
    if product_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Товара не существует"
        )

    user = await get_user_by_cookie(session, request)
    stmt = insert(UsersProducts).values(
        users_id=user["user_id"],
        products_id=product_id,
        quantity=1,
        status=product_status.value,
    )
    await session.execute(stmt)
    await session.commit()
    return ApiStatus(status="success", message="Товар добавлен в корзину")


async def change_product_status_to_cart(
    slug: str,
    stat: ProductStatus,
    request: Request,
    session: AsyncSession,
):
    product_id = await get_product(slug, session)
    if product_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Товара не существует"
        )
    user = await get_user_by_cookie(session, request)
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
    return ApiStatus(status="success", message="Товар добавлен в корзину")


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
                # mock
                UsersProducts.status == "processing",
            )
        )
        .group_by(Products.id)
    )
    result = await session.execute(stmt)
    return result.mappings().all()


async def show_cart_short(
    user: UsersJwtDecode,
    session: AsyncSession,
):
    stmt = (
        select(Products)
        .distinct()
        .join(UsersProducts, Products.id == UsersProducts.products_id)
        .where(
            and_(
                UsersProducts.users_id == user["user_id"],
                UsersProducts.status == "processing",
            )
        )
    )
    result = await session.execute(stmt)
    # по умолчанию [] если пусто
    return result.scalars().all()


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
        "category": "Тип",
        "price": "Ценовой диапазон",
        "colors": "Цвет",
        "volume": "Объем",
    }
    stmt = select(Products.filters, Products.price).limit(1)
    row = (await session.execute(stmt)).mappings().first()

    filters = row["filters"]
    price = row["price"]

    filters_name = list(filters.keys())
    show_filters = []
    for filter_name in filters_name:
        if filter_name in FILTER_LABELS.keys():
            show_filters.append(FILTER_LABELS[filter_name])
    show_filters.append(FILTER_LABELS["price"])
    return show_filters


# для отображения существующих значений для каждого фильтра
async def get_filters_values(session: AsyncSession):

    stmt = select(
        func.min(Products.price).label("min_price"),
        func.max(Products.price).label("max_price"),
        func.array_agg(func.distinct(Products.filters["category"].astext)).label(
            "categories"
        ),
        func.array_agg(func.distinct(Products.filters["colors"].astext)).label(
            "colors"
        ),
        func.array_agg(func.distinct(Products.filters["volume"].as_integer())).label(
            "volumes"
        ),
    )

    result = await session.execute(stmt)
    data = result.mappings().first()

    return FiltersValues(
        price_range={
            "min_price": data["min_price"] or 0,
            "max_price": data["max_price"] or 12000,
        },
        categories=data["categories"],
        colors=data["colors"],
        volumes=data["volumes"],
    )


async def find_product_by_filters(filters: FiltersFind, session: AsyncSession):
    stmt = select(Products)
    print(f"Фильтры: {filters}")
    conditions = []

    for name, values in filters.model_dump().items():
        if values is None:
            continue
        if len(values) == 1:
            # число
            if isinstance(values[0], int):
                conditions.append(Products.filters[name].as_integer() == values[0])
            # строка
            if isinstance(values[0], str):
                conditions.append(Products.filters[name].astext == values[0])
        # обязательно сначала на словарь проверить
        if name == "priceRange" and isinstance(values, dict):
            conditions.append(
                and_(
                    Products.price >= values["min_price"],
                    Products.price <= values["max_price"],
                )
            )
            continue
        elif isinstance(values[0], int):
            or_conditions = [
                Products.filters[name].as_integer() == value for value in values
            ]
            conditions.append(or_(*or_conditions))
        # список строк
        elif isinstance(values[0], str):
            or_conditions = [Products.filters[name].astext == value for value in values]
            conditions.append(or_(*or_conditions))

    stmt = stmt.where(and_(*conditions))
    result = await session.execute(stmt)
    res = result.scalars().all()
    return res


async def product_comment_add(session, product_id, feedback):
    stmt = ProductsFeedback(
        sender_id=feedback.sender_id,
        product_id=product_id,
        comment=feedback.comment,
    )
    session.add(stmt)
    await session.commit()
    return ApiStatus(status="success", message="Комментарий оставлен")


async def get_reviewers_by_product(
    session: AsyncSession, product_id: int
) -> list[GetProductReviewers]:
    stmt = (
        select(
            Users.id.label("id_reviewer"),
            Users.name.label("name_reviewer"),
            Users.date_registration.label("date_registration_reviewer"),
            Users.photo.label("photo_reviewer"),
            ProductsFeedback.comment.label("comment"),
            ProductsFeedback.created_at.label("created_at"),
            # первый элемент (индекс 1 в PostgresSQL)
            Products.photos[1].astext.label("photo_product"),
        )
        .select_from(ProductsFeedback)
        .join(Users, Users.id == ProductsFeedback.sender_id)
        .join(Products, Products.id == ProductsFeedback.product_id)
        .where(Products.id == product_id)
    )
    result = await session.execute(stmt)
    # scalars().all() вернул бы массив с первым полем
    data = result.mappings().all()
    users = [GetProductReviewers.model_validate(row) for row in data]
    return users
