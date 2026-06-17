from sqlalchemy import select, insert, or_, and_, desc, func, case, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Users, WebsocketFriendlyMessage
from core.websocket.friendly.schemas import DialogResponse


async def get_user_by_url_id_or_id(
    session: AsyncSession,
    id: int | None = None,
    url_id: str | None = None,
):
    stmt = select(Users.id, Users.name, Users.url_id)
    if url_id:
        stmt = stmt.where(Users.url_id == url_id)

    elif id:
        stmt = stmt.where(Users.id == id)
    result = await session.execute(stmt)
    res = result.mappings().first()
    return {
        "id": res["id"],
        "username": res["name"],
        "url_id": res["url_id"],
    }


async def insert_ws_friendly_message(
    from_url_id: str,
    to_url_id: str,
    sender: str,
    recipient: str,
    message: str,
    type_message: str,
    session: AsyncSession,
    is_read_message: bool = False,
):
    print(f"insert_ws_friendly_message, is_read_message={is_read_message}")
    stmt = insert(WebsocketFriendlyMessage).values(
        from_url_id=from_url_id,
        to_url_id=to_url_id,
        sender=sender,
        recipient=recipient,
        message=message,
        type_message=type_message,
        is_read_message=is_read_message,
    )
    await session.execute(stmt)
    await session.commit()


async def get_history_dialog(
    session: AsyncSession,
    url_id: str,
    to_url_id: str,
):
    stmt = (
        select(
            WebsocketFriendlyMessage.id,
            WebsocketFriendlyMessage.sender,
            WebsocketFriendlyMessage.recipient,
            WebsocketFriendlyMessage.message,
            WebsocketFriendlyMessage.created_at,
            case(
                (WebsocketFriendlyMessage.from_url_id == url_id, True), else_=False
            ).label("is_own"),
        )
        .where(
            or_(
                # сообщения от url_id к to_url_id
                and_(
                    WebsocketFriendlyMessage.from_url_id == url_id,
                    WebsocketFriendlyMessage.to_url_id == to_url_id,
                ),
                # сообщения от to_url_id к url_id
                and_(
                    WebsocketFriendlyMessage.from_url_id == to_url_id,
                    WebsocketFriendlyMessage.to_url_id == url_id,
                ),
            )
        )
        .order_by(WebsocketFriendlyMessage.created_at)
    )

    result = await session.execute(stmt)
    rows = result.mappings().all()

    # Добавим лог для отладки
    print(f"🔍 Найдено сообщений для диалога {url_id} <-> {to_url_id}: {len(rows)}")

    return [
        {
            "id": str(row["id"]),
            "sender": row["sender"],
            "recipient": row["recipient"],
            "message": row["message"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "is_own": row["is_own"],
        }
        for row in rows
    ]


async def get_dialog_last_message(
    session: AsyncSession,
    from_url_id: str,
    to_url_id: str,
):
    stmt = (
        select(WebsocketFriendlyMessage)
        .where(
            and_(
                WebsocketFriendlyMessage.from_url_id == from_url_id,
                WebsocketFriendlyMessage.to_url_id == to_url_id,
            )
            | and_(
                WebsocketFriendlyMessage.from_url_id == to_url_id,
                WebsocketFriendlyMessage.to_url_id == from_url_id,
            )
        )
        .order_by(WebsocketFriendlyMessage.created_at.desc())
        .limit(1)
    )

    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_history_dialogs(
    session: AsyncSession,
    url_id: str,
):
    subquery = (
        select(
            func.least(
                WebsocketFriendlyMessage.from_url_id,
                WebsocketFriendlyMessage.to_url_id,
            ).label("user_a"),
            func.greatest(
                WebsocketFriendlyMessage.from_url_id,
                WebsocketFriendlyMessage.to_url_id,
            ).label("user_b"),
            func.max(WebsocketFriendlyMessage.created_at).label("max_created"),
        )
        .where(
            or_(
                WebsocketFriendlyMessage.from_url_id == url_id,
                WebsocketFriendlyMessage.to_url_id == url_id,
            )
        )
        .group_by("user_a", "user_b")
        .subquery()
    )
    stmt = (
        select(
            WebsocketFriendlyMessage.id,
            WebsocketFriendlyMessage.from_url_id,
            WebsocketFriendlyMessage.to_url_id,
            WebsocketFriendlyMessage.recipient,
            WebsocketFriendlyMessage.sender,
            WebsocketFriendlyMessage.message,
            WebsocketFriendlyMessage.created_at,
            WebsocketFriendlyMessage.is_read_message,
            case(
                (WebsocketFriendlyMessage.from_url_id == url_id, True), else_=False
            ).label("is_own"),
        )
        .join(
            subquery,
            and_(
                func.least(
                    WebsocketFriendlyMessage.from_url_id,
                    WebsocketFriendlyMessage.to_url_id,
                )
                == subquery.c.user_a,
                func.greatest(
                    WebsocketFriendlyMessage.from_url_id,
                    WebsocketFriendlyMessage.to_url_id,
                )
                == subquery.c.user_b,
                WebsocketFriendlyMessage.created_at == subquery.c.max_created,
            ),
        )
        .order_by(desc(WebsocketFriendlyMessage.created_at))
    )

    result = await session.execute(stmt)
    rows = result.mappings().all()
    return [
        DialogResponse.model_validate(data).model_dump(mode="json") for data in rows
    ]


async def unread_messages(
    session: AsyncSession,
    url_id: str,
):
    # Есть не прочитанное - верну True
    stmt = select(WebsocketFriendlyMessage.is_read_message).where(
        WebsocketFriendlyMessage.to_url_id == url_id,
    )
    res = await session.execute(stmt)
    messages = res.scalars().all()
    for read_message in messages:
        if not read_message:
            return True
    return False


async def mark_dialog_as_read(
    session: AsyncSession,
    current_url_id: str,
    interlocutor_url_id: str,
):
    stmt = (
        update(WebsocketFriendlyMessage)
        .where(
            and_(
                WebsocketFriendlyMessage.from_url_id == interlocutor_url_id,
                WebsocketFriendlyMessage.to_url_id == current_url_id,
                WebsocketFriendlyMessage.is_read_message == False,
            )
        )
        .values(is_read_message=True)
    )

    await session.execute(stmt)
    await session.commit()
