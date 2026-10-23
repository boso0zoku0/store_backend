from pydantic import BaseModel


class UsersProductsBase(BaseModel):
    users_id: int
    products_id: int
    quantity: int


class SuggestedUsers(BaseModel):
    id: int
    name: str
    url_id: str
    bought_products: int | None = None

    class Config:
        from_attributes = True
