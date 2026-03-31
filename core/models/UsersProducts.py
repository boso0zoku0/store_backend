import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ENUM
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
    from core.models import Users


class ProductStatus(enum.Enum):
    processing = "processing"
    moving = "moving"
    completed = "completed"
    cancelled = "cancelled"
    none = "none"


class UsersProducts(Base):
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    users_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    products_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
    )
    status = mapped_column(
        ENUM(ProductStatus, name="product_status", create_type=True),
        default=ProductStatus.none.value,
        nullable=True,
    )
    quantity: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
