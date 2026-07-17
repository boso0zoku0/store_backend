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
