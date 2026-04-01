from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from sqlalchemy.ext.asyncio import AsyncSession
from core import db_helper
from core.payments.crud import add_payment

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
