from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from core.users import get_user_by_cookie


async def add_payment(request: Request, session: AsyncSession):
    user = get_user_by_cookie(session, request)
