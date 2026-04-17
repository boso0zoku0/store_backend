from typing import Annotated
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, Request, Path
from core.models.UsersProducts import ProductStatus
from core.websocket.notify.manager import manager
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket, WebSocketDisconnect
from core import db_helper
from core.websocket.crud import get_user_from_cookies

router = APIRouter()


@router.websocket("/notify")
async def users_ws(
    websocket: WebSocket,
    username: Annotated[str, Query()],
    url_id: Annotated[str, Query()],
    product_name: Annotated[str, Query()],
):
    await websocket.accept()
    await manager.connect(url_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "notify_manager":
                await manager.broadcast(
                    username=data["username"],
                    url_id=data["url_id"],
                    product_name="Piala",
                )
    except WebSocketDisconnect:
        await manager.disconnect(url_id)
