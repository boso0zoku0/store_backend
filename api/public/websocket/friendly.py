from typing import Annotated
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core import db_helper
from core.websocket.friendly.crud import (
    get_user_by_url_id_or_id,
    get_history_dialogs,
    mark_dialog_message,
    get_history_dialog,
)
from core.websocket.friendly.manager import friendly_manager as manager

router = APIRouter()


@router.get("/user/by")
async def get_user(
    url_id: Annotated[str, Query()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_user_by_url_id_or_id(session, url_id=url_id)


@router.get("/get-dialogs")
async def get_dialogs(
    url_id: Annotated[str, Query()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_history_dialogs(session, url_id=url_id)


@router.get("/mark-message")
async def mark_message_as_read(
    current_url_id: Annotated[str, Query()],
    interlocutor_url_id: Annotated[str, Query()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await mark_dialog_message(
        session,
        current_url_id=current_url_id,
        interlocutor_url_id=interlocutor_url_id,
        is_read_message=True,
    )


@router.websocket("/friendly/dialog")
async def users_ws(
    sock: WebSocket,
    url_id: Annotated[str, Query(...)],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    await sock.accept()
    manager.connect(url_id, sock)
    try:
        while True:
            data = await sock.receive_json()

            if data and data["type"] == "request_dialogs_history":
                await manager.get_dialogs(
                    url_id=data["url_id"],
                    session=session,
                )

            elif data and data["type"] == "request_dialog_history":
                await manager.get_dialog(
                    url_id=data["from_url_id"],
                    to_url_id=data["to_url_id"],
                    session=session,
                )

            elif data and data["type"] == "client_msg":
                await manager.send_message(
                    from_user_url_id=data["from_url_id"],
                    to_user_url_id=data["to_url_id"],
                    sender=data["sender"],
                    recipient=data["recipient"],
                    message=data["message"],
                    session=session,
                )

    except WebSocketDisconnect:
        manager.disconnect(url_id)
