from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def add_payment(request: Request, session: AsyncSession):
    # user = get_user_by_cookie(session, request)
    pass
