from typing import Optional, List

from pydantic import BaseModel


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
