from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Products


async def get_product(slug: str, session: AsyncSession):
    stmt = select(Products.id).where(Products.slug == slug)
    result = await session.execute(stmt)
    return result.scalars().first()
