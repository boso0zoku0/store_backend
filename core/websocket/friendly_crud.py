from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Users

import json
from sqlalchemy import insert, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import WebSocket, WebSocketException, Request, Depends
from core import db_helper
from core.models import WebsocketFriendlyMessage, Users
from core.models.websock_friendly_msg import WsFriendlyTypeMessage


async def get_user_by_url_id(session: AsyncSession, url_id: str):
    stmt = select(Users.name).where(Users.url_id == url_id)
    result = await session.execute(stmt)
    res = result.scalars().first()
    return {"username": res}


async def insert_ws_friendly_message(
    from_user_id: int,
    to_user_id: int,
    sender: str,
    recipient: str,
    message: str,
    type_message: str,
    session: AsyncSession,
):
    stmt = insert(WebsocketFriendlyMessage).values(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        sender=sender,
        recipient=recipient,
        message=message,
        type_message=type_message,
    )
    await session.execute(stmt)
    await session.commit()
