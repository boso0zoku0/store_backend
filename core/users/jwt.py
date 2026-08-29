from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import jwt
from core.schemas.users import UsersJwtDecode

BASE_DIR = Path(__file__).parent.parent


class JWTHelper:
    def __init__(self):
        self.public_key = BASE_DIR / "jwt_keys" / "jwt_public.pem"
        self.private_key = BASE_DIR / "jwt_keys" / "jwt_private.pem"
        self.algorithm = "RS256"
        self.access_token_expire_minutes = 900
        self.refresh_token_expire_days = 30

    def encode(
        self,
        payload: dict,
        token_type: Literal["access", "refresh"],
    ) -> str:
        now = datetime.now(timezone.utc)
        data = payload.copy()
        if token_type == "access":
            data.update(
                {
                    "exp": now + timedelta(minutes=self.access_token_expire_minutes),
                    "iat": now,
                    "type": token_type,
                }
            )
        elif token_type == "refresh":
            data.update(
                {
                    "exp": now + timedelta(days=self.refresh_token_expire_days),
                    "iat": now,
                    "type": token_type,
                }
            )

        return jwt.encode(data, self.private_key.read_text(), self.algorithm)

    def decode(self, token: str | bytes) -> UsersJwtDecode:
        return jwt.decode(
            token,
            self.public_key.read_text(),
            self.algorithm,
        )


jwt_helper = JWTHelper()
