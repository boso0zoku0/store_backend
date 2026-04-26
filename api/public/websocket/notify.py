from typing import Annotated
from core.websocket.notify.manager import manager
from fastapi import APIRouter, Depends, Query
from starlette.websockets import WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/notify")
async def users_ws(
    websocket: WebSocket,
    url_id: Annotated[str, Query()],
):
    print("WS ЗАШЛИ")
    await websocket.accept()
    await manager.connect(url_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            print("Получил из data", data)
            if data["type"] == "notify_manager":
                await manager.broadcast(
                    username=data["username"],
                    url_id=data["url_id"],
                    product_name=data["product_name"],
                )
    except WebSocketDisconnect:
        print("Закрыли подключерие")
    finally:
        manager.disconnect(url_id)
