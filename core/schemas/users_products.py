from pydantic import BaseModel


class UsersProductsBase(BaseModel):
    users_id: int
    products_id: int
    quantity: int
