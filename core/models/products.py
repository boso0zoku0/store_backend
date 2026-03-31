import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from pydantic import BaseModel
from sqlalchemy import func, ForeignKey, Integer, Numeric
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
    from core.models import Users
    from core.models import UsersProducts


class Filters(BaseModel):
    categories: Optional[List[str]] = None
    priceRange: Optional[List[int]] = None  # или Tuple[float, float]
    colors: Optional[List[str]] = None
    volume: Optional[List[int]] = None
    inStock: Optional[bool] = None


class Products(Base):
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    short_name: Mapped[str] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[int] = mapped_column(nullable=True)
    filters: Mapped[Filters] = mapped_column(
        JSONB,
        nullable=True,
        default=lambda: {
            "categories": [""],
            "price_range": (0, 50000),
            "colors": [""],
            "volume": [0, 0],
            "in_stock": True,
        },
    )

    description: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        unique=True,
        default=lambda: {
            "type": "",
            "color": "",
            "volume": "",
            "diameter": "",
            "specificity": "",
        },
    )
    photos: Mapped[list[str]] = mapped_column(JSONB, nullable=True)
    about: Mapped[str] = mapped_column(Text, nullable=True)

    users: Mapped[list["Users"]] = relationship(
        "Users",
        back_populates="products",
        secondary="usersproducts",
    )
