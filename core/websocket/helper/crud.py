import json
from datetime import datetime, timedelta, timezone

from fastapi import Depends, WebSocketException
from sqlalchemy import select, or_, and_, insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.websockets import WebSocket

from core import db_helper
from core.models import WebsocketMessageHistory, WebsocketConnections, Users
from core.users.crud import get_user_by_cookie


async def get_user_dialog(
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
    client: str | None = None,
    operator: str | None = None,
):
    time_range = datetime.now(timezone.utc) - timedelta(days=30)

    # Базовый запрос
    stmt = (
        select(WebsocketMessageHistory)
        .where(
            WebsocketMessageHistory.created_at > time_range,
            and_(
                WebsocketMessageHistory.operator == operator,
                WebsocketMessageHistory.client == client,
            ),
        )
        .order_by(WebsocketMessageHistory.created_at)
    )
    result = await session.execute(stmt)
    dialog_history = result.scalars().all()
    print(f"dialog_history: {dialog_history}")

    return dialog_history


async def insert_ws_connections(
    session: AsyncSession,
    username: str,
    user_id: int,
    ip_address: str,
    user_agent: str,
    is_active: bool,
    connection_type: str,
):
    stmt = insert(WebsocketConnections).values(
        username=username,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        is_active=is_active,
        connection_type=connection_type,
    )
    await session.execute(stmt)
    await session.commit()


async def insert_ws_message_history(
    message: str,
    type_message: str,
    file_url: str | None = None,
    mime_type: str | None = None,
    from_user_id: int | None = None,
    to_user_id: int | None = None,
    client: str | None = None,
    operator: str | None = None,
    is_resolved: bool = False,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    stmt = insert(WebsocketMessageHistory).values(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        message=message,
        type_message=type_message,
        client=client,
        operator=operator,
        file_url=file_url,
        mime_type=mime_type,
        is_resolved=is_resolved,
    )
    await session.execute(stmt)
    await session.commit()


async def get_user_by_name(
    username: str,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    stmt = select(Users.id).where(Users.name == username)
    result = await session.execute(stmt)
    res = result.scalars().first()
    return res


async def get_user_from_cookies(websocket: WebSocket, session: AsyncSession):

    headers = dict(websocket.scope.get("headers", []))
    cookie_header = headers.get(b"cookie", b"").decode()

    cookies = {}
    for cookie in cookie_header.split(";"):
        if "=" in cookie:
            key, value = cookie.strip().split("=", 1)
            cookies[key] = value

    session_id = cookies.get("session_id")

    if not session_id:
        raise WebSocketException(code=1008)
    headers = dict(websocket.scope.get("headers", []))
    user_agent = headers.get(b"user-agent", b"").decode()
    ip = websocket.client.host if websocket.client else "0.0.0.0"

    stmt = select(Users).where(Users.cookie == session_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    return {
        "id": user.id,
        "username": user.name,
        "headers": headers,
        "user_agent": user_agent,
        "ip": ip,
    }


async def parse(msg):
    if isinstance(msg, bytes):
        msg_str = msg.decode("utf-8", errors="ignore")

        msg = json.loads(msg_str)

    if isinstance(msg, str):
        try:
            return json.loads(msg)
        except json.JSONDecodeError:
            return {"message": msg}
    else:
        return msg
