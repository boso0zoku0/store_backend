from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field
from typing import Literal

import logging
import os

BASE_DIR = Path(__file__).parent.parent


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
    db_url: str = "postgresql+asyncpg://postgres:matvei225CC@localhost:5432/store"
    db_echo: bool = True
    naming_convention: dict[str, str] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(column_0_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }


class Setting(BaseSettings):
    api_v1_prefix: str = "/api/v1"
    db: DatabaseConfig = DatabaseConfig()
    logging: LoggingConfig = LoggingConfig()


settings = Setting()


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData(naming_convention=settings.db.naming_convention)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{cls.__name__.lower()}"
