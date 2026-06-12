from datetime import datetime, timezone
from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    Request,
    UploadFile,
    File,
)
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from broker.config import broker, queue_operators, exchange, queue_clients
from core import db_helper
from core.models import WebsocketConnections
from core.websocket.helper.crud import get_user_dialog, get_user_from_cookies
from core.websocket.helper.manager import manager
import logging


from services.s3.s3_client import s3_client

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/get-clients")
async def clients():
    return await manager.get_clients()


@router.post("/upload/")
async def upload_media(
    file: UploadFile = File(...),
):
    result = await s3_client.upload_file(file)
    return result


@router.websocket("/operator/{operator}")
async def operator_ws(
    websocket: WebSocket,
    operator: str,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    await websocket.accept()
    print("Оператор подключился")
    user = await get_user_from_cookies(websocket, session)
    await manager.connect_operator(
        session=session,
        websocket=websocket,
        operator=operator,
        user_id=user["id"],
        ip_address=user["ip"],
        user_agent=user["user_agent"],
        is_active=True,
    )

    try:
        while True:
            data: dict = await websocket.receive_json()

            msg_type = data.get("type")
            if msg_type == "accept_client":
                await manager.connect_confirm_to_client(
                    operator=data["from"],
                    client=data["to"],
                )
            elif msg_type == "file_url":
                await broker.publish(
                    message={
                        "operator": data["from"],
                        "client": data["to"],
                        "message": data.get("message", ""),
                        "mime_type": data.get("mime_type", ""),
                        "file_url": data.get("file_url", ""),
                    },
                    queue=queue_operators,
                    exchange=exchange,
                    # routing_key="operators",
                )
            elif msg_type == "operator_message" or (
                msg_type is None and "message" in data
            ):
                await manager.send_to_client(
                    session=session,
                    operator=data["from"],
                    client=data["to"],
                    message=data["message"],
                )

            else:
                log.warning(f"⚠️ Неизвестный тип сообщения: {data}")

    except WebSocketDisconnect:
        if operator in manager.operators:
            await session.execute(
                update(WebsocketConnections)
                .where(WebsocketConnections.username == operator)
                .values(is_active=False, disconnected_at=datetime.now(tz=timezone.utc))
            )
            await session.commit()
            del manager.operators[operator]
        log.info("✗ Оператор отключился")
    except Exception as e:
        log.info(f"Ошибка: {e}")


@router.get("/get-user-dialog")
async def show_user_dialog(
    request: Request,
    operator: str | None = Query(None),
    client: str | None = Query(None, description="имя клиента для фильтрации"),
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    return await get_user_dialog(
        session=session, client=client, operator=operator, request=request
    )


@router.websocket("/clients/{client}")
async def clients_ws(
    websocket: WebSocket,
    client: str,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    await websocket.accept()
    user = await get_user_from_cookies(websocket, session)

    await manager.connect_client(
        session=session,
        websocket=websocket,
        user_id=user["id"],
        client=client,
        ip_address=user["ip"],
        user_agent=user["user_agent"],
        is_active=True,
        is_advertising=True,
    )
    log.info(f"Клиент {client} подключился")
    try:
        while True:
            data = await websocket.receive_json()
            handler_bot = await manager.sender_bot(
                client=client,
                message=data["message"],
            )

            if not handler_bot and "to" in data and not "file_url" in data:
                await broker.publish(
                    message={
                        "client": data["from"],
                        "operator": data["to"],
                        "message": data.get("message", ""),
                    },
                    queue=queue_clients,
                    exchange=exchange,
                )
            # elif not handler_bot:
            #     log.info("Кликает по ответу бота")
            elif "file_url" in data:
                await broker.publish(
                    message={
                        "client": data["from"],
                        "operator": data["to"],
                        "message": data.get("message", ""),
                        "file_url": data.get("file_url", ""),
                        "mime_type": data.get("mime_type", ""),
                    },
                    queue=queue_clients,
                    exchange=exchange,
                )

    except WebSocketDisconnect:
        await session.execute(
            update(WebsocketConnections)
            .where(WebsocketConnections.username == client)
            .values(is_active=False, disconnected_at=datetime.now(tz=timezone.utc))
        )
        await session.commit()
        """Через брокер disconnect_client не вызывается почему то. напрямую всё ок"""
        await manager.disconnect_client(client=client)

    # await broker.publish(
    #     message={
    #         "from": client,
    #         "type": "disconnect_client",
    #     }
    # )
