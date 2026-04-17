from fastapi import WebSocket


class WebsocketManager:
    def __init__(self):
        self.users: dict[str, WebSocket] = {}

    async def connect(self, url_id, websocket: WebSocket):
        self.users[url_id] = websocket

    async def broadcast(
        self,
        url_id: str,
        username: str,
        product_name: str,
    ):
        print("BROADCAST")
        for user_id, websocket in self.users.items():
            await websocket.send_json(
                {
                    "type": "notify_manager",
                    "from": username,
                    "url_id": url_id,
                    "product_name": product_name,
                }
            )

    async def disconnect(self, url_id):
        del self.users[url_id]


manager = WebsocketManager()
