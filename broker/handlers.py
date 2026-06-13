import json

from core import db_helper
from core.websocket.helper.manager import manager
from broker.config import (
    broker,
    queue_operators,
    queue_clients,
    exchange,
)


# @broker.subscriber(queue=queue_notify_client, exchange=exchange)
# async def handler_notifying_client(msg: dict):
"""
    Теперь вызываю эту функцию напрямую из websocket manager
"""
#     if msg["type"] == "advertising":
#         await manager.advertising_to_client(
#             client=msg["client"], message=msg["message"]
#         )


@broker.subscriber(queue=queue_clients, exchange=exchange)
async def handler_from_client_to_operator(
    msg: dict | str | bytes,
):
    async with db_helper.session_factory() as session:
        if msg["type"] == "media":
            await manager.send_media_to_operator(
                session=session,
                client=msg.get("client"),
                operator=msg.get("operator"),
                message=msg.get("message"),
                mime_type=msg.get("mime_type"),
                file_url=msg.get("file_url"),
            )
        elif msg["type"] == "client":
            await manager.send_to_operator(
                session=session,
                client=msg["client"],
                operator=msg["operator"],
                message=msg["message"],
            )


@broker.subscriber(queue=queue_operators, exchange=exchange)
async def handler_from_operator_to_client(msg: dict):
    async with db_helper.session_factory() as session:
        if msg["type"] == "media":
            await manager.send_media_to_client(
                session=session,
                operator=msg["from"],
                client=msg["to"],
                message=msg["message"],
                mime_type=msg["mime_type"],
                file_url=msg["file_url"],
            )
        elif msg["type"] == "operator":
            await manager.send_to_client(
                session=session,
                operator=msg["from"],
                client=msg["to"],
                message=msg["message"],
            )
