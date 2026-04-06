"""
Admin API authentication dependency.

Requires the X-Admin-Key header to match the ADMIN_API_KEY env var / settings.
If ADMIN_API_KEY is not configured (None), all requests are rejected with 403
to prevent accidentally running without authentication.
"""

from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.config import settings

_api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def require_admin_key(key: str | None = Security(_api_key_header)) -> None:
    """Raise HTTP 401 if the request does not supply the correct admin API key."""
    configured_key = settings.admin_api_key
    if configured_key is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin API key not configured — set ADMIN_API_KEY env var.",
        )
    if key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
