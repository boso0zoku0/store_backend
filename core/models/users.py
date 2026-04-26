import enum
import os
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import func, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from core.config import Base
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy import (
    Text,
    Identity,
    create_engine,
    CheckConstraint,
    func,
    text,
    BigInteger,
)

if TYPE_CHECKING:
    from core.models import Products


class Users(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    password: Mapped[str] = mapped_column(nullable=False, unique=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=True)
    phone: Mapped[str] = mapped_column(Text, unique=True, nullable=True)
    date_registration: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    user_role: Mapped[str] = mapped_column(default="client")
    url_id: Mapped[str] = mapped_column(unique=True, nullable=True)
    cookie: Mapped[str] = mapped_column(nullable=True)
    ip: Mapped[str] = mapped_column(nullable=True)
    cookie_expires: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        server_default=text("TIMEZONE('utc', now()) + interval '5 minutes'"),
    )

    products: Mapped["Products"] = relationship(
        "Products",
        back_populates="users",
        secondary="usersproducts",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
    )

    helper_ws_from_user = relationship(
        "WebsocketMessageHistory",
        foreign_keys="WebsocketMessageHistory.from_user_id",
        back_populates="from_user",
    )
    helper_ws_to_user = relationship(
        "WebsocketMessageHistory",
        foreign_keys="WebsocketMessageHistory.to_user_id",
        back_populates="to_user",
    )

    friendly_ws_from_user = relationship(
        "WebsocketFriendlyMessage",
        foreign_keys="WebsocketFriendlyMessage.from_user_id",
        back_populates="from_user",
    )
    friendly_ws_to_user = relationship(
        "WebsocketFriendlyMessage",
        foreign_keys="WebsocketFriendlyMessage.to_user_id",
        back_populates="to_user",
    )
