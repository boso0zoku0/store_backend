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


async def get_user_by_url_id_or_id(
    session: AsyncSession,
    id: int | None = None,
    url_id: str | None = None,
):
    stmt = select(Users.id, Users.name, Users.url_id)
    if url_id is not None:
        stmt = stmt.where(Users.url_id == url_id)

    elif id is not None:
        stmt = stmt.where(Users.id == id)
    result = await session.execute(stmt)
    res = result.mappings().first()
    return {
        "id": res["id"],
        "username": res["name"],
        "url_id": res["url_id"],
    }


async def insert_ws_friendly_message(
    from_user_url_id: str,
    to_user_url_id: str,
    sender: str,
    recipient: str,
    message: str,
    type_message: str,
    session: AsyncSession,
):
    stmt = insert(WebsocketFriendlyMessage).values(
        from_user_url_id=from_user_url_id,
        to_user_url_id=to_user_url_id,
        sender=sender,
        recipient=recipient,
        message=message,
        type_message=type_message,
    )
    await session.execute(stmt)
    await session.commit()
