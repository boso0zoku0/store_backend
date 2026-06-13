import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import WebSocket

from core.models import PendingMessages
from core.websocket.helper.crud import (
    insert_ws_connections,
    insert_ws_message_history,
    get_user_by_name,
)
from services.redis.config import redis_client

log = logging.getLogger(__name__)


async def get_list_games():  # For Websockets
    return ["game_one", "game_two"]


async def get_list_genres():  # For Websockets
    return ["genre_one", "genre_two", "genre_three"]


class WebsocketManager:
    def __init__(self):
        self.operators: dict[str, WebSocket] = {}
        self.clients: dict[str, WebSocket] = {}
        self.redis = redis_client
        self.clients_ask = "chats:helper:clients_ask"
        self.visited_chat = "chats:helper:visit:chat"
        self.dialogs_info = "chats:helper:dialogs_info"
        # {
        # path: chats:helper:clients_ask
        #   'operator1': {
        #       'client1':'2020-10-03:14:50:10', 'client2':'2020-11-03:14:50:10',
        #   },
        #
        # path chats:helper:dialogs_info
        # {
        #   'operator1': {
        #       'client1': '19.05.2000:14:44',
        #       'client2': '19.01.2005:16:14',
        #     }
        # 'operator2': {
        #       'client3': '19.05.2000:14:44',
        #       'client4': '19.01.2005:16:14',
        #     }
        # }
        self.dialog_data: defaultdict[str, dict[str, datetime]] = defaultdict(dict)

        self._background_task = None

    async def connect_client(
        self,
        websocket: WebSocket,
        client: str,
        ip_address: str,
        user_agent: str,
        is_active: bool,
        user_id: int,
        session: AsyncSession,
        is_advertising: bool = False,
    ):
        self.clients[client] = websocket
        await insert_ws_connections(
            session=session,
            username=client,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=is_active,
            connection_type="client",
        )
        if await self.redis.hexists(self.visited_chat, client):
            return
        await self.init_communication_with_client(client)
        await self.redis.hset(self.visited_chat, client, "1")
        # Логика с отправкой рекламы в чат, позже доделать
        # if is_advertising:
        #     stmt = (
        #         select(PendingMessages)
        #         .where(PendingMessages.user_id == user_id)
        #         .limit(1)
        #     )
        #     res = await session.execute(stmt)
        #     message = res.scalar_one_or_none()
        #     if not message:
        #         return
        #     await self.advertising_to_client(
        #         client=client,
        #         message=message.message,
        #     )
        #     await session.delete(message)

    async def connect_operator(
        self,
        websocket: WebSocket,
        operator: str,
        user_id: int,
        ip_address: str,
        user_agent: str,
        is_active: bool,
        session: AsyncSession,
    ):

        self.operators[operator] = websocket
        await insert_ws_connections(
            session=session,
            username=operator,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=is_active,
            connection_type="operator",
        )

    async def get_clients(self):
        return await self.redis.hkeys(self.clients_ask)

    async def send_to_operator(
        self,
        session: AsyncSession,
        client: str,
        operator: str,
        message: str,
    ):
        # Нужна проверка в случае если оператор уже вышел из чата, клиент пишет исходя из operator.current данных, но не знает, что его уже нет
        current_operator = None
        if operator in self.operators:
            current_operator = operator
            await self.operators[operator].send_json(
                {
                    "type": "client",
                    "from": client,
                    "to": operator,
                    "message": message,
                }
            )
            # self.dialog_data[operator][client] = datetime.now()
            await self.redis.hset(
                f"{self.dialogs_info}:{operator}",
                client,
                datetime.now().isoformat(),
            )
        from_user_id = await get_user_by_name(client, session)
        to_user_id = (
            await get_user_by_name(operator, session)
            if operator in self.operators
            else None
        )

        await insert_ws_message_history(
            session=session,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            client=client,
            operator=current_operator,
            message=message,
            type="client",
        )

    async def send_to_client(
        self,
        session: AsyncSession,
        client: str,
        operator: str,
        message: str,
    ):
        try:
            if client in self.clients:
                await self.clients[client].send_json(
                    {
                        "type": "operator",
                        "from": operator,
                        "to": client,
                        "message": message,
                    }
                )
                # self.dialog_data[operator][client] = datetime.now()
                await self.redis.hset(
                    f"{self.dialogs_info}:{operator}",
                    client,
                    datetime.now().isoformat(),
                )
            from_user_id = await get_user_by_name(operator, session)
            to_user_id = (
                await get_user_by_name(client, session)
                if client in self.clients
                else None
            )
            await insert_ws_message_history(
                session=session,
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                client=client,
                operator=operator,
                message=message,
                type="operator",
            )

            trigger_disconnect: str = "У вас остались вопросы?"
            if message == trigger_disconnect:
                await self.start_timeout_checker(operator, client)

            log.info(f"✓ Сообщение отправлено клиенту {client}: {message}")
        except Exception as e:
            log.info(f"✗ Ошибка отправки {operator} -> {client}")

    async def disconnect_client(self, client: str, operator: str):
        try:
            if client in self.clients:
                self.clients.pop(client)
            if await self.redis.hexists(self.clients_ask, client):
                await self.redis.hdel(self.clients_ask, client)
                log.info(f"✓ Клиент {client} удален из self.clients")
            await self.notify_disconnect_to_operator(client, operator)
            # del self.dialog_data[operator][client]
            await self.redis.hdel(f"{self.dialogs_info}:{operator}", client)
            log.info(f"клиент → Удален из диалога с оператором {operator}")
        except Exception as e:
            log.error(f"✗ Ошибка при отключении клиента {client}: {operator}")

    async def connect_request_to_operators(
        self,
        client: str,
    ):
        # busy_operators = set(self.dialog_data.keys())
        busy_operators = await self.redis.hkeys(self.dialogs_info)

        for op in self.operators.keys():
            if op not in busy_operators:
                await self.operators[op].send_json(
                    {
                        "type": "connect_request",
                        "from": client,
                        "to": op,
                    }
                )
                print("busy_operator:", op)

    async def connect_confirm_to_client(self, client: str, operator: str):
        # self.dialog_data[operator][client] = datetime.now()
        await self.redis.hset(
            f"{self.dialogs_info}:{operator}",
            client,
            datetime.now().isoformat(),
        )
        await self.redis.hset(
            f"{self.dialogs_info}:{operator}",
            client,
            datetime.now().isoformat(),
        )
        await self.clients[client].send_json(
            {
                "type": "connect_confirm",
                "from": operator,
                "to": client,
                "message": f"Оператор {operator} вошел в чат",
            }
        )
        # Пришел к выводу, что send_json логика на бэке не нужна, на фронте отправляю и так
        # connect_confirm, а вот в локальный словарь надо сохранять кого то(клиента и оператора наверно)
        # Возможная проблема, на фронте в useRef прокидываю имя оператора, а на бэке
        # не успеваю добавить его в словарь

    async def bot_ask_question_about_solving_problem(
        self, client: str, operator: str, message: str
    ):
        """Как узнать связку оператора с клиентом в busy_operators - итерироваться по k,v - если v это клиент, значит k - оператор который с ним вел диалог"""

        current_time = datetime.now()
        # last_message_time = self.dialog_data[operator][client]
        last_message_time = await self.redis.hget(
            f"{self.dialogs_info}:{operator}",
            client,
        )
        if last_message_time + timedelta(minutes=1) < current_time:
            await self.clients[client].send_json(
                {
                    "type": "bot",
                    "message": "Did you manage to resolve the issue?",
                }
            )

    async def client_answer_to_question_about_solving_problem(
        self, client: str, operator: str, message: str, session: AsyncSession
    ):
        from_user_id = await get_user_by_name(client, session)

        if message == "Yes":
            # del self.dialog_data[operator][client]
            await self.redis.hdel(f"{self.dialogs_info}:{operator}", client)
            await insert_ws_message_history(
                message=message,
                type="client",
                from_user_id=from_user_id,
                client=client,
                operator=operator,
                is_resolved=True,
                session=session,
            )

    async def sender_bot(self, client: str, message: str):
        # triggers_bot = {
        #     "View the movie catalog": lambda: get_list_games(),
        #     "View the genre catalog": lambda: get_list_genres(),
        #     "Find out the creator of the website": "The creator comes from a small town. The site was created in 2026 as part of a single developer",
        #     "Call the operator with command - 'help me'": "The operator is already rushing to you",
        # }
        triggers_operator = {"help me", "call the operator"}
        if any(trigger in message for trigger in triggers_operator):
            await self.clients[client].send_json(
                {
                    "type": "bot",
                    "message": "Оператор оповещен о вашем запросе",
                }
            )
            await self.redis.hset(self.clients_ask, client, message)
            await self.connect_request_to_operators(client)
            return True
        # Проверка на остальные команды в боте
        # for question, response in triggers_bot.items():
        #     if question in message:
        #         if callable(response):
        #             answer = await response()
        #         else:
        #             answer = response
        #         await self.clients[client].send_json(
        #             {
        #                 "type": "bot_message",
        #                 "message": answer,
        #             }
        #         )
        #         return True
        return False

    async def init_communication_with_client(self, client: str):
        await self.clients[client].send_json(
            {
                "type": "greeting",
                "message": [
                    f"Hello, {client}, how can I help you?",
                    "1)View the movie catalog",
                    "2) View the genre catalog",
                    "3) Find out the creator of the website",
                    "4) Call the operator with command - 'help me'",
                ],
            }
        )

    async def advertising_to_client(self, client: str, message: str):
        await self.clients.get(client).send_json(
            {
                "type": "advertising",
                "to": client,
                "message": message,
            }
        )

    async def send_media_to_client(
        self,
        session: AsyncSession,
        operator: str,
        client: str,
        file_url: str,
        mime_type: str,
        message: str = "",
    ):
        from_user_id = await get_user_by_name(operator, session)
        to_user_id = await get_user_by_name(client, session) if client else None
        await insert_ws_message_history(
            session=session,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            client=client,
            operator=operator,
            message=message,
            type="media",
            file_url=file_url,
            mime_type=mime_type,
        )
        if client:
            await self.clients[client].send_json(
                {
                    "type": "media",
                    "from": operator,
                    "to": client,
                    "message": message,
                    "file_url": file_url,
                    "mime_type": mime_type,
                }
            )

    async def send_media_to_operator(
        self,
        session: AsyncSession,
        client: str,
        operator: str,
        file_url: str,
        mime_type: str,
        message: str = "",
    ):
        from_user_id = await get_user_by_name(client, session)
        to_user_id = await get_user_by_name(operator, session) if operator else None
        await self.clients[client].send_json(
            {
                "type": "media",
                "from": client,
                "to": operator,
                "message": message,
                "file_url": file_url,
                "mime_type": mime_type,
            }
        )
        await insert_ws_message_history(
            session=session,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            client=client,
            operator=operator,
            message=message,
            type="media",
            file_url=file_url,
            mime_type=mime_type,
        )
        if operator:
            await self.operators[operator].send_json(
                {
                    "type": "media",
                    "from": client,
                    "to": operator,
                    "message": message,
                    "file_url": file_url,
                    "mime_type": mime_type,
                }
            )

    # Поправить логику, ведь на фронте вроде мы это ловим и закрываем чат полностью у оператора
    async def notify_disconnect_to_operator(self, client: str, operator: str):
        await self.operators[operator].send_json(
            {
                "type": "disconnect",
                "from": client,
            }
        )

    async def start_timeout_checker(self, operator: str, client: str):
        """Запускаем фоновую проверку таймаутов"""
        if self._background_task is None:
            self._background_task = asyncio.create_task(
                self._check_timeouts(operator, client)
            )

    async def _check_timeouts(self, operator: str, client: str):
        while True:
            try:
                if not self.redis.hexists(f"{self.dialogs_info}:{operator}", client):
                    # if not self.dialog_data[operator].get(client):
                    break
                await asyncio.sleep(10)  # Проверка каждые 10 секунд
                await self._check_last_msg_operator_with_client(operator, client)
            except Exception as e:
                print(f"Error in timeout checker: {e}")

    async def _check_last_msg_operator_with_client(self, operator: str, client: str):
        now = datetime.now()
        # last_msg_time = self.dialog_data[operator][client]
        last_msg_time = self.redis.hget(f"{self.dialogs_info}:{operator}", client)
        if now > last_msg_time + timedelta(seconds=10):
            await self.disconnect_client(client, operator)


manager = WebsocketManager()
