from contextlib import asynccontextmanager

from fastapi import FastAPI
from faststream.rabbit import RabbitExchange, RabbitQueue
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from api.public.products import router as products_router_public
from api.public.auth import router as auth_router
from api.protected.products import router as products_router_protected
from api.protected.users import router as users_router
from api.public.weather import router as weather_router
from api.public.websocket import router as websocket_router_public
from broker.config import (
    broker,
    exchange,
    queue_clients,
    queue_notify_client,
    queue_operators,
)

# exchange = RabbitExchange("exchange_chat")
# # queue_clients_greeting = RabbitQueue("greeting_with_clients")
# # queue_notifying_client_operator = RabbitQueue("notifying_client_operator_connection")
# queue_notify_client = RabbitQueue("notify_client")
# queue_clients = RabbitQueue("from_clients")
# queue_operators = RabbitQueue("from_operators")

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # 1. Подключение к брокеру
#     await broker.connect()
#     print("✅ Broker connected")
#
#     # 2. Создание exchange и получение объекта exchange
#     exchange = RabbitExchange("exchange_chat", durable=True, auto_delete=False)
#     exchange_obj = await broker.declare_exchange(exchange)
#     print("✅ Exchange declared")
#
#     # 3. Создание очередей и получение объектов очередей
#     queue_clients_obj = await broker.declare_queue(queue_clients)
#     queue_operators_obj = await broker.declare_queue(queue_operators)
#     queue_notify_client_obj = await broker.declare_queue(queue_notify_client)
#     print("✅ Queues declared")
#
#     await queue_clients_obj.bind(exchange_obj, routing_key="clients")
#     await queue_operators_obj.bind(exchange_obj, routing_key="operators")
#     await queue_notify_client_obj.bind(exchange_obj, routing_key="notify")
#
#     yield
#
#     await broker.close()
#     print("❌ Broker closed")
#
#     await broker.close()
#     print("❌ Broker closed")


app = FastAPI()


app.include_router(products_router_public)
app.include_router(products_router_protected)
app.include_router(websocket_router_public)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(weather_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://clay-shop.ru",
        "https://www.clay-shop.ru",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы
    allow_headers=["*"],  # Разрешаем все заголовки
)
app.mount("/static", StaticFiles(directory="static"), name="static")
# Отключаем автоматический редирект со слешем


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
