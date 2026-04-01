from sqlalchemy.orm import DeclarativeBase, declared_attr
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field
from typing import Literal
import logging
import os

BASE_DIR = Path(__file__).parent.parent


class Base(DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{cls.__name__.lower()}"


class LoggingConfig(BaseModel):
    log_level_name: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: str = (
        "[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s"
    )
    date_format: str = "%Y-%m-%d %H:%M:%S"

    @property
    def log_level(self) -> int:
        return logging.getLevelNamesMapping()[self.log_level_name]


class Setting(BaseSettings):
    api_v1_prefix: str = "/api/v1"
    db_url: str = "postgresql+asyncpg://postgres:matvei225CC@localhost:5432/store"
    db_echo: bool = True
    logging: LoggingConfig = LoggingConfig()


settings = Setting()
