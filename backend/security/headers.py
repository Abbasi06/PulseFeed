"""
HTTP security headers middleware (OWASP hardening).

Applied as the outermost middleware so these headers appear on every
response, including CORS preflight replies and error pages.

Headers added
-------------
  X-Content-Type-Options      nosniff — prevents MIME-type sniffing
  X-Frame-Options             DENY    — blocks clickjacking
  X-XSS-Protection            0       — disabled; CSP is the modern guard
  Referrer-Policy             strict-origin-when-cross-origin
  Permissions-Policy          opt-out all powerful browser features
  Strict-Transport-Security   1-year HSTS with subdomains
  Content-Security-Policy     restrictive default-src 'self' policy
"""
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=(), payment=()",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self'"
    ),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response: Response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
