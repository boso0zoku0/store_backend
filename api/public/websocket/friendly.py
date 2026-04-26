from typing import Annotated
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core import db_helper
from core.websocket.friendly_crud import get_user_by_url_id
from core.websocket.friendly.manager import friendly_manager as manager

router = APIRouter()


@router.get("/user/by")
async def get_user(
    url_id: Annotated[str, Query()],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_user_by_url_id(session, url_id)


@router.websocket("/friendly/dialog")
async def users_ws(
    sock: WebSocket,
    url_id: Annotated[str, Query(...)],
):
    await sock.accept()
    room_id = manager.generate_id_room()
    print("ROOM ID:", room_id)
    manager.join_room(url_id, room_id)
    try:
        while True:
            data = await sock.receive_json()
            if data:
                manager.send_message(
                    room_id=room_id,
                    from_user=data["from_user"],
                    to_user=data["to_user"],
                    message=data["message"],
                )

    except WebSocketDisconnect:
        manager.disconnect(room_id, url_id)
