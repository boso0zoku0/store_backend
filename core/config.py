from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field
from typing import Literal

import logging
import os

BASE_DIR = Path(__file__).parent.parent
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB_COUNT = os.getenv("REDIS_DB_COUNT")


class LoggingConfig(BaseModel):
    log_level_name: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: str = (
        "[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s"
    )
    date_format: str = "%Y-%m-%d %H:%M:%S"

    @property
    def log_level(self) -> int:
        return logging.getLevelNamesMapping()[self.log_level_name]


class DatabaseConfig(BaseModel):
    db_url: str = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
    )
    db_echo: bool = True
    naming_convention: dict[str, str] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(column_0_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }


class RedisConfig(BaseModel):
    redis_url: str = (
        f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_COUNT}"
    )


class Setting(BaseSettings):
    api_v1_prefix: str = "/api/v1"
    db: DatabaseConfig = DatabaseConfig()
    logging: LoggingConfig = LoggingConfig()
    redis: RedisConfig = RedisConfig()


settings = Setting()


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData(naming_convention=settings.db.naming_convention)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{cls.__name__.lower()}"
