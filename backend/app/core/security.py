from datetime import datetime, timezone
from hashlib import sha256
from secrets import token_urlsafe

from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def new_access_token() -> str:
    return token_urlsafe(32)


def hash_access_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()
