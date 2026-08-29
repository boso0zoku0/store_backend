from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator, field_serializer


class Description(BaseModel):
    type: str
    color: str
    volume: str
    diameter: str
    specificity: str


class ProductBase(BaseModel):
    id: int
    name: str
    short_name: Optional[str] = None
    price: Optional[int] = None
    photos: Optional[List[str]] = None
    about: Optional[str] = None


class ProductSearchResult(ProductBase):
    similarity_percent: float


class ProductsGet(ProductBase):
    pass


class ProductsPost(ProductBase):
    slug: str


class FiltersValues(BaseModel):
    price_range: dict[str, int]
    categories: list[str]
    colors: list[str]
    volumes: list[int]


class FiltersFind(BaseModel):
    category: list[str] | None = None
    colors: list[str] | None = None
    volume: list[int] | None = None
    priceRange: dict[str, int] | None = None


class ProductCommentAdd(BaseModel):
    sender_id: int
    comment: str = Field(..., min_length=1, max_length=200)

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: str):
        if len(v) < 1:
            raise ValueError(f"The comment is too short")
        if len(v) > 200:
            raise ValueError(f"The comment is too long")
        return v


class GetProductReviewers(BaseModel):
    id_reviewer: int
    name_reviewer: str
    comment: str
    created_at: datetime
    date_registration_reviewer: datetime
    photo_reviewer: str
    photo_product: str

    @field_serializer("date_registration_reviewer")
    def serialize_dt_user(self, dt: datetime) -> str:
        # Формат: 15.01.2024 10:30
        return dt.strftime("%d.%m.%Y %H:%M")

    @field_serializer("created_at")
    def serialize_dt_comment(self, dt: datetime) -> str:
        # Формат: 15.01.2024 10:30
        return dt.strftime("%d.%m.%Y %H:%M")


class Filters(BaseModel):
    category: str = ""
    colors: str = ""
    volume: int | None = None


class Product(BaseModel):
    id: int
    name: str
    short_name: str | None = None
    slug: str | None = None
    price: int | None = None
    filters: Filters | None = None
    description: dict | None = None
    photos: list[str] | None = None
    about: str | None = None


class ProductCart(Product):
    quantity: list[int] | None = None
