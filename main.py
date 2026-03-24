from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from products.views import router as products_router
from users.views import router as users_router

app = FastAPI()
app.include_router(products_router)
app.include_router(users_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5175",
        "http://localhost:5174",
        "https://bosozoku-shop.cloudpub.ru",
        "http://localhost:5173",
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
