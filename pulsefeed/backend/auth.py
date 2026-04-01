"""
JWT helpers for PulseFeed.

Token is stored in an httpOnly cookie named `access_token`.
SameSite=Lax allows same-host cross-port requests (localhost:5173 → localhost:8000)
without requiring HTTPS in development.
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, HTTPException
from jose import JWTError, jwt

SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-before-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30

COOKIE_OPTS: dict = dict(
    key="access_token",
    httponly=True,
    samesite="lax",
    secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
    path="/",
    max_age=TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def get_current_user_id(access_token: str | None = Cookie(default=None)) -> int:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _decode_token(access_token)
