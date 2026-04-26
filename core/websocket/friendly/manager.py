import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from starlette.websockets import WebSocket

from core.websocket.helper_crud import insert_ws_message_history


class WebsocketManager:
    def __init__(self):
        self.users: dict[str, WebSocket] = {}
        self.sessions: dict[str, dict[str, Any]] = defaultdict(dict)

    @staticmethod
    def generate_id_room():
        return str(uuid.uuid4())

    def join_room(self, url_id: str, sock: WebSocket, room_id: str | None = None):
        now = datetime.now()
        self.users[url_id] = sock
        self.sessions[room_id].update({url_id: now})
        print("JOIN ROOM ID:", self.sessions.get(room_id).get(url_id))

    def send_message(self, room_id: str, from_user: str, to_user: str, message: str):
        now = datetime.now()
        # Доработать вставку в таблицу ws_friendly
        if self.sessions.get(room_id) and self.sessions[room_id].get(from_user):
            self.sessions[room_id][from_user] = now
            self.users[from_user].send_json(
                {
                    "type": "friendly_message",
                    "room_id": room_id,
                    "from": from_user,
                    "to": to_user,
                    "message": message,
                    "timestamp": now,
                }
            )
        # elif not self.sessions.get(room_id) or not self.sessions[room_id].get(
        #     from_user
        # ):
        #     pass
        else:
            # Проблема - юзер первый пишет юзеру второму, но того, нет в сети - поэтому будет ошибка
            # Задача - обрабатывать случаи когда юзер не в сети.
            # Вариант - класть сообщения просто в бд. А если все таки в сети, то в бд и по вебсокету
            if self.users.get(from_user):
                self.users[from_user].send_json(
                    {
                        "type": "error during sending message",
                    }
                )
            else:
                print("ЮЗЕРА ЕЩЕ НЕТ")

    def disconnect(self, room_id: str, url_id: str):
        self.sessions[room_id].pop(url_id, None)
        self.users.pop(url_id, None)


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
