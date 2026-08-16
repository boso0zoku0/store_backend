from sqlalchemy import (
    Identity,
    String,
    Text,
    BigInteger,
    Integer,
    ForeignKey,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.config import Base


class ProductsFeedback(Base):
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    comment: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
