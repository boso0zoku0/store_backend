from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DialogResponse(BaseModel):
    id: UUID
    from_url_id: str
    to_url_id: str
    recipient: str
    sender: str
    message: str
    created_at: datetime
    is_own: bool
    interlocutor: str
    is_read_message: bool
    interlocutor: str | None = None
