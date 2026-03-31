from pydantic import BaseModel


class Description(BaseModel):
    type: str
    color: str
    volume: str
    diameter: str
    specificity: str


class ProductsBase(BaseModel):
    name: str
    short_name: str
    price: int
    description: Description | None = None
    photos: list[str] | None = None
    about: str | None = None


class ProductsGet(ProductsBase):
    id: int


class ProductsPost(ProductsBase):
    slug: str
