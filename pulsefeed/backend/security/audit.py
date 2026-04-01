"""
Security audit middleware.

Emits a structured WARNING log for every 401, 403, and 429 response.

Fields logged
-------------
  status    HTTP status code
  method    HTTP verb
  path      URL path  (no query string — avoids leaking search params)
  ip        Client IP address
  ts        ISO-8601 UTC timestamp

Deliberately excluded
---------------------
  Request/response headers, cookies, bearer tokens, request bodies,
  user IDs, query parameters, usernames, or any other PII.
"""
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

audit_logger = logging.getLogger("pulsefeed.audit")

_AUDIT_STATUSES = frozenset({401, 403, 429})


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response: Response = await call_next(request)

        if response.status_code in _AUDIT_STATUSES:
            ip = request.client.host if request.client else "unknown"
            audit_logger.warning(
                "SECURITY_EVENT status=%d method=%s path=%s ip=%s ts=%s",
                response.status_code,
                request.method,
                request.url.path,
                ip,
                datetime.now(timezone.utc).isoformat(),
            )

        return response
