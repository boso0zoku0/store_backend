import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from starlette.websockets import WebSocket


class WebsocketManager:
    def __init__(self):
        self.users: dict[str, WebSocket] = {}
        self.sessions: dict[str, dict[str, Any]] = defaultdict(dict)

    @staticmethod
    def generate_id_room():
        return str(uuid.uuid4())

    def create_room(self, url_id: str, sock: WebSocket, room_id: str | None = None):
        generate_room_id = self.generate_id_room()
        now = datetime.now()
        self.users[url_id] = sock
        self.sessions[generate_room_id].update({url_id: now})

    def join_room(self, url_id: str, room_id: str, sock: WebSocket):
        now = datetime.now()
        self.sessions[room_id].update({url_id: now})

    def send_message(self, room_id: str, from_user: str, to_user: str, message: str):
        now = datetime.now()
        if self.sessions.get(room_id) and self.sessions[room_id].get(from_user):
            self.sessions[room_id][from_user] = now
            self.users[from_user].send_json(
                {
                    "type": "user_message",
                    "room_id": room_id,
                    "from": from_user,
                    "to": to_user,
                    "message": message,
                    "timestamp": now,
                }
            )
        else:
            self.users[from_user].send_json(
                {
                    "type": "error during sending message",
                }
            )

    def disconnect(self, room_id: str, url_id: str):
        self.sessions[room_id].pop(url_id, None)
        self.users.pop(url_id, None)


friendly_manager = WebsocketManager()
# {
#     "@hjfdhj$28qj" {
#         "users_1": "...",
#         "users_2": "...",
#     }
#     "#$32fewfkjq": {
#         "users_1": "...",
#         "users_2": "...",
#     }
# }
