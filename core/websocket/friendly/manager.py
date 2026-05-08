import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket

from core.websocket.friendly.crud import (
    get_user_by_url_id_or_id,
    insert_ws_friendly_message,
)


class WebsocketManager:
    def __init__(self):
        self.users: dict[str, WebSocket] = {}

    def connect(self, url_id, sock: WebSocket):
        self.users[url_id] = sock

    async def send_message(
        self,
        from_user_url_id: str,
        to_user_url_id: str,
        sender: str,
        recipient: str,
        message: str,
        session: AsyncSession,
    ):
        await self.users[to_user_url_id].send_json(
            {
                "friendly_message": message,
                "sender": sender,
                "recipient": recipient,
                "message": message,
            }
        )
        await insert_ws_friendly_message(
            from_user_url_id=from_user_url_id,
            to_user_url_id=to_user_url_id,
            sender=sender,
            recipient=recipient,
            message=message,
            type_message="client",
            session=session,
        )

    def disconnect(self, url_id: str):
        self.users.pop(url_id, None)

    @staticmethod
    def generate_id_room():
        return str(uuid.uuid4())


friendly_manager = WebsocketManager()
# {
#     "@hjfdhj$28qj" {
#         "users_1": "date",
#         "users_2": "date",
#     }
#     "#$32fewfkjq": {
#         "users_1": "date",
#         "users_2": "date"
#     }
# }
