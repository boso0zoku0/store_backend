import os
from typing import Annotated

import httpx
from fastapi import (
    Form,
    Depends,
    HTTPException,
    Body,
    APIRouter,
    Response,
    status,
    Request,
)
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from core import db_helper
from core.models import Users
from core.users.crud import add_user, login
from core.users.helper import generate_session_id
from core.users.jwt import jwt_helper

router = APIRouter(
    tags=["Weather"],
)


@router.post("/weather", status_code=status.HTTP_200_OK)
async def get_weather(req: Request):
    ip = req.client.host
    key_api_ip = "5fde3e4516f747fb998d11a627bdf9d3"
    key_weather_map = "8c0cb36d801f13182db8a44c44d12b0b"
    async with httpx.AsyncClient() as client:
        say_city = await client.get(
            f"https://api.ipgeolocation.io/v3/ipgeo?apiKey={key_api_ip}&ip={ip}"
        )
        city = say_city.json()["location"]["city"]
        say_lat_lon = await client.get(
            f"https://api.openweathermap.org/geo/1.0/direct?q={city}&limit=5&appid={key_weather_map}"
        )
        lon = say_lat_lon.json()["lon"]
        lat = say_lat_lon.json()["lat"]
        response = await client.get(
            f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={key_weather_map}"
        )
        return response.json().weather.description
