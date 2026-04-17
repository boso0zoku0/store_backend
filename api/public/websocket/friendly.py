from typing import Annotated

from fastapi import APIRouter, Query
from starlette.websockets import WebSocket, WebSocketDisconnect
from core.websocket.friendly.manager import friendly_manager as manager

router = APIRouter()


@router.websocket("/users/dialog/")
async def users_ws(
    sock: WebSocket,
    url_id: Annotated[str, Query(...)],
    room_id: Annotated[str | None, Query()] = None,
):
    print("dweqdfwq wqd wqd q wqd wqd q")
    await sock.accept()
    await manager.create_room(url_id, room_id)
    try:
        while True:
            data = await sock.receive_json()
            if data:
                await manager.send_message(
                    room_id=data["room_id"],
                    from_user=data["from_user"],
                    to_user=data["to_user"],
                    message=data["message"],
                )

    except WebSocketDisconnect:
        await manager.disconnect(room_id, url_id)
