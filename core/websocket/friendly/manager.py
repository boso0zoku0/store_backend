import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket

from core.models import WebsocketFriendlyMessage
from core.websocket.friendly.crud import (
    insert_ws_friendly_message,
    get_history_dialog,
    get_history_dialogs,
    get_dialog_last_message,
    unread_messages,
)
from services.redis.config import redis_client


class WebsocketManager:
    def __init__(self):
        self.users: dict[str, WebSocket] = {}
        self.redis = redis_client

    def connect(self, url_id, sock: WebSocket):
        self.users[url_id] = sock

    async def track_open_dialog(self, url_id: str, to_url_id: str):
        sort_key = sorted([url_id, to_url_id])
        dialog_key = f"{sort_key[0]}:{sort_key[1]}"
        active_users = await self.redis.hget(
            "chats:friendly",
            dialog_key,
        )

        # # Пустой диалог
        if active_users is None:
            print(f"🔵 Пустой диалог, кладу только отправителя: {url_id}")
            await self.redis.hset("chats:friendly", dialog_key, url_id)
            return False
        # Мой собеседник активен сейчас, а я до этого момента
        # был не активен, значит положить меня тоже
        elif not url_id in active_users and to_url_id in active_users:
            print(
                f"🟢 Получатель активен, добавляю отправителя: dialog_key={dialog_key}"
            )
            await self.redis.hset("chats:friendly", dialog_key, dialog_key)
            return True
        # В диалоге два участника
        elif url_id in active_users and to_url_id in active_users:
            return True
        # Только я в диалоге
        elif url_id in active_users and to_url_id not in active_users:
            print(f"🟡 Отправитель активен, получатель нет — ничего не меняю")
            return False

    async def track_close_dialog(self, url_id: str, to_url_id: str):
        sort_key = sorted([url_id, to_url_id])
        dialog_key = f"{sort_key[0]}:{sort_key[1]}"
        dialog_data = await self.redis.hget("chats:friendly", dialog_key)

        if dialog_data is not None and url_id in dialog_data:
            # При закрытии узнал, что собеседника уже нет
            if to_url_id not in dialog_data:
                await self.redis.hdel(
                    "chats:friendly",
                    dialog_key,
                )
            else:
                await self.redis.hset(
                    "chats:friendly",
                    dialog_key,
                    to_url_id,
                )
                await self.users[to_url_id].send_json(
                    {
                        "type": "friend_leave",
                        "url_id_friend": url_id,
                    }
                )

    # Получить все сообщения диалога
    async def get_dialog(self, url_id: str, to_url_id: str, session: AsyncSession):
        messages = await get_history_dialog(
            session,
            url_id=url_id,
            to_url_id=to_url_id,
        )
        await self.users[url_id].send_json(
            {
                "type": "response_dialog_history",
                "message": messages,
            }
        )
        await self.track_open_dialog(url_id, to_url_id)

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

    # Вызывается при открытии вебсокета и при отправке или получении сообщения
    async def has_unread_messages(
        self,
        session: AsyncSession,
        url_id_curr: str,
    ):

        # При открытии вебсокета
        message = await unread_messages(session, url_id=url_id_curr)
        await self.users[url_id_curr].send_json(
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

        print(f"вызвал send_message, параметры from - {from_url_id} ; to - {to_url_id}")
        is_open_dialog = await self.track_open_dialog(
            url_id=from_url_id,
            to_url_id=to_url_id,
        )
        is_read_message = is_open_dialog
        await insert_ws_friendly_message(
            from_url_id=from_url_id,
            to_url_id=to_url_id,
            sender=sender,
            recipient=recipient,
            message=message,
            type_message="client",
            session=session,
            is_read_message=is_read_message,
        )

        if to_url_id in self.users:
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
