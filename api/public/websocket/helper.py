from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, Request
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from broker.config import broker, queue_operators, exchange, queue_clients
from core import db_helper
from core.models import WebsocketConnections
from core.websocket.helper_crud import get_user_from_cookies, get_user_dialog
from core.websocket.helper.manager import manager
import logging

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/get-clients")
async def clients():
    return await manager.get_clients()


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
            log.info(f"🔍 ПОЛУЧЕНО: {data}")

            msg_type = data.get("type")
            if msg_type == "notify_connect_to_client":
                await manager.notify_connect_to_client(
                    client=data["to"], operator=data["from"]
                )
            elif "file_url" in data or msg_type == "media":
                await broker.publish(
                    message={
                        "type": "media",
                        "from": data["from"],
                        "to": data["to"],
                        "message": data.get("message", ""),
                        "mime_type": data["mime_type"],
                        "file_url": data["file_url"],
                    },
                    queue=queue_operators,
                    exchange=exchange,
                    routing_key="operators",
                )
            elif msg_type == "operator_message" or (
                msg_type is None and "message" in data
            ):
                log.info(
                    f"💬 Сообщение от {data['from']} для {data['to']}: {data.get('message')}"
                )
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
    operator: str | None = Query(
        None, description="для оператора, чтобы запросить диалог с конкретным клиентом"
    ),
    username: str | None = Query(None, description="имя клиента для фильтрации"),
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    if username is None:
        return await get_user_dialog(session=session, request=request)
    return await get_user_dialog(
        session=session, username=username, operator=operator, request=request
    )


@router.websocket("/clients/{client}")
async def clients_ws(
    websocket: WebSocket,
    client: str,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    print("ВОШЛИ в функцию")
    await websocket.accept()
    print("Accept выполнен")

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
                session=session,
                websocket=websocket,
            )
            if not handler_bot and "to" in data:
                log.info(f"data: {data['from']} ; {data['message']}")
                await manager.send_to_operator(
                    session=session,  # ← 1. session
                    client=data["from"],  # ← 2. client
                    operator=data["to"],  # ← 3. operator
                    message=data["message"],  # ← 4. message
                )
            # elif not handler_bot:
            #     log.info("Кликает по ответу бота")

            if "file_url" in data:
                await broker.publish(
                    message={
                        "from": data["from"],
                        "to": data["to"],
                        "message": data.get("message", ""),
                        "mime_type": data["mime_type"],
                        "file_url": data["file_url"],
                    },
                    queue=queue_clients,
                    exchange=exchange,
                    routing_key="clients",
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
