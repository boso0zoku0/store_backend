import datetime as dt
import enum
import uuid
from sqlalchemy import func, ForeignKey, String, Integer, DateTime, Enum, UUID, false
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


class WsFriendlyTypeMessage(enum.Enum):
    bot = "bot"
    client = "client"


class WebsocketFriendlyMessage(Base):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    from_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    to_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    sender: Mapped[str] = mapped_column(Text, nullable=True)
    recipient: Mapped[str] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type_message: Mapped[WsFriendlyTypeMessage] = mapped_column(
        Enum(WsFriendlyTypeMessage, name="type_message"), nullable=False
    )
    created_at: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    from_user = relationship(
        "Users",
        foreign_keys=[from_user_id],
        back_populates="friendly_ws_from_user",
        cascade="all, delete",
    )
    to_user = relationship(
        "Users",
        foreign_keys=[to_user_id],
        back_populates="friendly_ws_to_user",
        cascade="all, delete",
    )
