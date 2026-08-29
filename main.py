import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from faststream.rabbit import RabbitExchange, RabbitQueue
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
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
from broker.handlers import *
from core.config import LoggingConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Подключение к брокеру
    await broker.start()
    print("✅ Broker connected")
    yield
    await broker.stop()
    print("❌ Broker closed")


app = FastAPI(lifespan=lifespan)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Глобальный обработчик всех SQLAlchemy ошибок"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Ошибка базы данных. Попробуйте позже."},
    )


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
