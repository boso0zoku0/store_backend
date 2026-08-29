from pydantic import BaseModel


# В случае ошибки возвращу HttpException дабы указать код ошибки,
# если вернуть данный класс в таком случае, будет считаться не корректно
class ApiStatus(BaseModel):
    status: str
    message: str
