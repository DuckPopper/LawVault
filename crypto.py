"""Encryption at rest (Fernet = AES-128-CBC + HMAC) and password/token hashing."""
from __future__ import annotations
import hashlib, hmac, secrets
from typing import Optional
import bcrypt
from cryptography.fernet import Fernet, InvalidToken
import config

_fernet = Fernet(config.APP_KEY)


def encrypt(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return _fernet.encrypt(text.encode("utf-8")).decode("ascii")


def decrypt(token: Optional[str]) -> str:
    if not token:
        return ""
    try:
        return _fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return "[unreadable]"


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


_DUMMY = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(rounds=12))


def verify_password(pw: str, hashed: Optional[str]) -> bool:
    """Always does one bcrypt check, so response time doesn't reveal whether the user exists."""
    target = hashed.encode("ascii") if hashed else _DUMMY
    ok = bcrypt.checkpw(pw.encode("utf-8"), target)
    return ok and hashed is not None


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hmac_code(code: str, salt: str) -> str:
    return hmac.new(config.HMAC_KEY, f"{salt}|{code}".encode(), hashlib.sha256).hexdigest()
