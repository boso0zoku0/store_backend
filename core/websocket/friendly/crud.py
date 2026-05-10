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
                (WebsocketFriendlyMessage.from_user_url_id == url_id, True), else_=False
            ).label("is_own"),
        )
        .where(
            or_(
                # сообщения от url_id к to_url_id
                and_(
                    WebsocketFriendlyMessage.from_user_url_id == url_id,
                    WebsocketFriendlyMessage.to_user_url_id == to_url_id,
                ),
                # сообщения от to_url_id к url_id
                and_(
                    WebsocketFriendlyMessage.from_user_url_id == to_url_id,
                    WebsocketFriendlyMessage.to_user_url_id == url_id,
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


async def get_history_dialogs(
    session: AsyncSession,
    url_id: str,
):
    subquery = (
        select(
            func.least(
                WebsocketFriendlyMessage.from_user_url_id,
                WebsocketFriendlyMessage.to_user_url_id,
            ).label("user_a"),
            func.greatest(
                WebsocketFriendlyMessage.from_user_url_id,
                WebsocketFriendlyMessage.to_user_url_id,
            ).label("user_b"),
            func.max(WebsocketFriendlyMessage.created_at).label("max_created"),
        )
        .where(
            or_(
                WebsocketFriendlyMessage.from_user_url_id == url_id,
                WebsocketFriendlyMessage.to_user_url_id == url_id,
            )
        )
        .group_by("user_a", "user_b")
        .subquery()
    )
    stmt = (
        select(
            WebsocketFriendlyMessage.id,
            WebsocketFriendlyMessage.from_user_url_id,
            WebsocketFriendlyMessage.to_user_url_id,
            WebsocketFriendlyMessage.recipient,
            WebsocketFriendlyMessage.sender,
            WebsocketFriendlyMessage.message,
            WebsocketFriendlyMessage.created_at,
            WebsocketFriendlyMessage.is_read_message,
            case(
                (WebsocketFriendlyMessage.from_user_url_id == url_id, True), else_=False
            ).label("is_own"),
        )
        .join(
            subquery,
            and_(
                func.least(
                    WebsocketFriendlyMessage.from_user_url_id,
                    WebsocketFriendlyMessage.to_user_url_id,
                )
                == subquery.c.user_a,
                func.greatest(
                    WebsocketFriendlyMessage.from_user_url_id,
                    WebsocketFriendlyMessage.to_user_url_id,
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


async def mark_dialog_message(
    session: AsyncSession,
    current_url_id: str,
    interlocutor_url_id: str,
    is_read_message: bool,
):
    subquery = (
        select(WebsocketFriendlyMessage.id)
        .where(
            and_(
                WebsocketFriendlyMessage.from_user_url_id == interlocutor_url_id,
                WebsocketFriendlyMessage.to_user_url_id == current_url_id,
            )
        )
        .order_by(desc(WebsocketFriendlyMessage.created_at))
        .limit(1)
        .scalar_subquery()
    )
    stmt = (
        update(WebsocketFriendlyMessage)
        .where(WebsocketFriendlyMessage.id == subquery)
        .values(is_read_message=is_read_message)
    )

    await session.execute(stmt)
    await session.commit()
