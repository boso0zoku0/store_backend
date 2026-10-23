from datetime import datetime, timedelta, timezone

from sqlalchemy import select, insert, or_, and_, desc, func, case, update, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
import logging.config
from core.models import Users, WebsocketFriendlyMessage
from core.schemas.auth import UserSchema
from core.schemas.users import UsersGetInfo

from core.users.crud import get_suggested_users, get_me
from core.websocket.friendly.schemas import DialogResponse
import logging
from fastapi import Request

log = logging.getLogger(__name__)
# id: UUID
# from_url_id: str
# to_url_id: str
# recipient: str
# sender: str
# message: str
# created_at: datetime
# is_own: bool
# is_read_message: bool


async def get_user_by_url_id_or_id(
    session: AsyncSession,
    my_url_id: str,
    interlocutor_url_id: str,
):
    my_stmt = select(Users.id, Users.name, Users.url_id, Users.photo).where(
        Users.url_id == my_url_id
    )
    my_result = await session.execute(my_stmt)
    my_data = my_result.mappings().first()
    interlocutor_stmt = select(Users.url_id, Users.name, Users.photo).where(
        Users.url_id == interlocutor_url_id
    )
    interlocutor_result = await session.execute(interlocutor_stmt)
    interlocutor_data = interlocutor_result.mappings().first()
    return {
        "id": my_data["id"],
        "from_photo": my_data["photo"],
        "username": interlocutor_data["name"],
        "to_photo": interlocutor_data["photo"],
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
    from_user = aliased(Users)
    to_user = aliased(Users)
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
            from_user.photo.label("from_photo"),
            to_user.photo.label("to_photo"),
        )
        .select_from(WebsocketFriendlyMessage)
        .join(from_user, from_user.url_id == WebsocketFriendlyMessage.from_url_id)
        .join(to_user, to_user.url_id == WebsocketFriendlyMessage.to_url_id)
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
            "is_own": bool(row["is_own"]),
            "from_photo": row["from_photo"],
            "to_photo": row["to_photo"],
            "last_seen": "",
        }
        for row in rows
    ]


async def get_user_photo(session: AsyncSession, url_id: str) -> str | None:
    stmt = select(Users.photo).where(Users.url_id == url_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


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
    from_user = aliased(Users)
    to_user = aliased(Users)
    # 1. Нумеруем сообщения внутри каждой пары по убыванию даты
    row_number = (
        func.row_number()
        .over(
            partition_by=(
                func.least(
                    WebsocketFriendlyMessage.from_url_id,
                    WebsocketFriendlyMessage.to_url_id,
                ),
                func.greatest(
                    WebsocketFriendlyMessage.from_url_id,
                    WebsocketFriendlyMessage.to_url_id,
                ),
            ),
            order_by=desc(WebsocketFriendlyMessage.created_at),
        )
        .label("rn")
    )

    subquery = (
        select(
            WebsocketFriendlyMessage.id.label("msg_id"),
            row_number,
        )
        .where(
            or_(
                WebsocketFriendlyMessage.from_url_id == url_id,
                WebsocketFriendlyMessage.to_url_id == url_id,
            )
        )
        .subquery()
    )

    # 2. Оставляем только rn = 1 — последнее сообщение в каждом диалоге
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
                (WebsocketFriendlyMessage.from_url_id == url_id, True),
                else_=False,
            ).label("is_own"),
            case(
                (
                    WebsocketFriendlyMessage.from_url_id == url_id,
                    to_user.photo,
                ),  # писал я → фото получателя
                else_=from_user.photo,  # писал он → фото отправителя
            ).label("interlocutor_photo"),
            from_user.photo.label("from_photo"),
            to_user.photo.label("to_photo"),
        )
        .join(from_user, from_user.url_id == WebsocketFriendlyMessage.from_url_id)
        .join(to_user, to_user.url_id == WebsocketFriendlyMessage.to_url_id)
        .join(subquery, subquery.c.msg_id == WebsocketFriendlyMessage.id)
        .where(subquery.c.rn == 1)
        .order_by(desc(WebsocketFriendlyMessage.created_at))
    )

    result = await session.execute(stmt)
    rows = result.mappings().all()
    if rows:
        return [
            DialogResponse.model_validate(data).model_dump(mode="json") for data in rows
        ]
    else:
        # диалогов нет
        log.info(f"No dialogs found for {url_id}")
        stmt = select(Users).where(Users.url_id == url_id)
        res = await session.execute(stmt)
        res_scalar = res.scalar_one_or_none()
        user = UserSchema.model_validate(res_scalar)
        return await get_suggested_users(session=session, user=user)


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
