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
    is_read_message: bool
    interlocutor: str | None = None
    interlocutor_photo: str | None = None
    from_photo: str | None = None
    to_photo: str | None = None
