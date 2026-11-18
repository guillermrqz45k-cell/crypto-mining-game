"""Auth: bcrypt directo + JWT (python-jose).

Se usa bcrypt directamente (sin passlib, incompatible con bcrypt>=4.1).
Las contrasenas se truncan a 72 bytes, limite de bcrypt.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import ALGORITHM, SECRET_KEY, ACCESS_TOKEN_EXPIRE_DAYS


def _to_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": subject, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
