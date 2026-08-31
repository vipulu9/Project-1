import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    return _encode(str(user_id), os.getenv("JWT_SECRET"), timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(user_id: int) -> str:
    return _encode(str(user_id), os.getenv("JWT_REFRESH_SECRET"), timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def decode_access_token(token: str) -> str:
    return _decode(token, os.getenv("JWT_SECRET"))


def decode_refresh_token(token: str) -> str:
    return _decode(token, os.getenv("JWT_REFRESH_SECRET"))


def _encode(subject: str, secret: str, expires: timedelta) -> str:
    payload = {
        "sub": subject,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + expires,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _decode(token: str, secret: str) -> str:
    # raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    return payload["sub"]
