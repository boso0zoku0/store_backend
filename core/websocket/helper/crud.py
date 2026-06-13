import json
from datetime import datetime, timedelta, timezone
from fastapi import Depends, WebSocketException, WebSocket, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, or_, and_, desc, func, case, update, asc
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
    # Пока что отвечаю на вопрос мое ли сообщение только от лица клиента, у оператора будет либо свой api либо этот доработать
    client_data = await get_user_by_cookie(session, request)
    stmt = (
        select(
            WebsocketMessageHistory,
            case(
                (WebsocketMessageHistory.from_user_id == client_data["user_id"], True),
                else_=False,
            ).label("is_own"),
        )
        .where(
            WebsocketMessageHistory.created_at > time_range,
            or_(
                # 1. Обычные сообщения (и operator, и client совпадают)
                and_(
                    WebsocketMessageHistory.operator == operator,
                    WebsocketMessageHistory.client == client,
                ),
                # 2. Медиа от клиента (operator пуст, client совпадает)
                and_(
                    WebsocketMessageHistory.operator == "",
                    WebsocketMessageHistory.client == client,
                ),
                and_(
                    WebsocketMessageHistory.operator.is_(None),
                    WebsocketMessageHistory.client == client,
                ),
                # 3. Медиа от оператора (client пуст, operator совпадает)
                and_(
                    WebsocketMessageHistory.client == "",
                    WebsocketMessageHistory.operator == operator,
                ),
                # 4. Сообщения в пустой диалог (если operator ещё не назначен)
                and_(
                    WebsocketMessageHistory.operator == "",
                    WebsocketMessageHistory.client == client,
                    WebsocketMessageHistory.type == "client",
                ),
            ),
        )
        .order_by(asc(WebsocketMessageHistory.created_at))
    )
    result = await session.execute(stmt)
    dialog_history = [
        {**row[0].__dict__, "is_own": row[1]}  # все поля сообщения  # добавляем is_own
        for row in result.all()
    ]
    for msg in dialog_history:
        msg.pop("_sa_instance_state", None)

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
    session: AsyncSession,
    message: str,
    type: str,
    file_url: str | None = None,
    mime_type: str | None = None,
    from_user_id: int | None = None,
    to_user_id: int | None = None,
    client: str | None = None,
    operator: str | None = None,
    is_resolved: bool = False,
):
    stmt = insert(WebsocketMessageHistory).values(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        message=message,
        type=type,
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
