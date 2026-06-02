import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket

from core.websocket.friendly.crud import (
    insert_ws_friendly_message,
    get_history_dialog,
    get_history_dialogs,
    get_dialog_last_message,
    unread_messages,
)


class WebsocketManager:
    def __init__(self):
        self.users: dict[str, WebSocket] = {}

    def connect(self, url_id, sock: WebSocket):
        self.users[url_id] = sock

    # Получить все сообщения диалога
    async def get_dialog(self, url_id: str, to_url_id: str, session: AsyncSession):
        messages = await get_history_dialog(session, url_id=url_id, to_url_id=to_url_id)
        await self.users[url_id].send_json(
            {
                "type": "response_dialog_history",
                "message": messages,
            }
        )

    # Получить последнее сообщение диалога
    async def get_last_message(
        self, from_url_id: str, to_url_id: str, session: AsyncSession
    ):
        message = await get_dialog_last_message(
            session, to_url_id=to_url_id, from_url_id=from_url_id
        )
        await self.users[from_url_id].send_json(
            {
                "type": "response_dialog_last_message",
                "message": message,
            }
        )

    async def has_unread_messages(self, url_id: str, session: AsyncSession):
        message = await unread_messages(session, url_id=url_id)
        await self.users[url_id].send_json(
            {
                "type": "response_is_new_message",
                "message": message,
            }
        )

    # Получить список последних сообщений диалогов
    async def get_dialogs(self, url_id: str, session: AsyncSession):
        messages = await get_history_dialogs(session, url_id)
        await self.users[url_id].send_json(
            {
                "type": "response_dialogs_history",
                "message": messages,
            }
        )

    async def send_message(
        self,
        from_url_id: str,
        to_url_id: str,
        sender: str,
        recipient: str,
        message: str,
        session: AsyncSession,
    ):
        now = datetime.now()
        if self.users.get(from_url_id) is not None:
            await self.users[to_url_id].send_json(
                {
                    "from_url_id": from_url_id,
                    "to_url_id": to_url_id,
                    "type": "client_msg",
                    "sender": sender,
                    "recipient": recipient,
                    "message": message,
                    "created_at": str(now),
                }
            )

        await self.users[from_url_id].send_json(
            {
                "from_url_id": from_url_id,
                "to_url_id": to_url_id,
                "type": "client_msg",
                "sender": sender,
                "recipient": recipient,
                "message": message,
                "created_at": str(now),
            }
        )
        await insert_ws_friendly_message(
            from_url_id=from_url_id,
            to_url_id=to_url_id,
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
