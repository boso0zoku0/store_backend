import secrets

import bcrypt


def hash_password(password: str) -> bytes:
    pwd_encode = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_encode, salt)


def validate_password(password: str, hashed_password: bytes) -> bool:
    return bcrypt.checkpw(
        password=password.encode("utf-8"), hashed_password=hashed_password
    )


def generate_session_id():
    return secrets.token_urlsafe()
