"""
Redis-backed fixed-window rate limiter.

Redis key schema
----------------
  rl:{scope}:{identifier}:{window_bucket}

  scope         short endpoint label, e.g. "feed_read", "telemetry"
  identifier    "user:{user_id}"  for auth'd endpoints
                "ip:{addr}"       for unauthenticated/IP-based endpoints
  window_bucket int(unix_time // window_seconds)  — current time bucket
  type          STRING (integer counter, incremented atomically)
  TTL           window_seconds * 2  — cleaned up after two windows

Fail-open strategy
------------------
  If Redis is unreachable or raises, rate limiting is bypassed and a
  WARNING is emitted.  This ensures dev/CI environments without Redis
  do not break; the operator is alerted that the guard is down.
"""
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Depends, HTTPException, Request

logger = logging.getLogger(__name__)


class RateLimiter:
    """Fixed-window counter backed by a shared Redis instance."""

    def __init__(self, limit: int, window: int = 60, scope: str = "default") -> None:
        self.limit = limit
        self.window = window
        self.scope = scope

    async def check(self, redis_client: Any, identifier: str) -> None:
        """
        Increment the counter for *identifier* in the current window.

        Raises HTTP 429 with a ``Retry-After`` header when the limit is
        exceeded.  Silently skips (fail-open) when *redis_client* is None
        or a Redis error occurs.
        """
        if redis_client is None:
            logger.warning(
                "Rate limiter: Redis unavailable — skipping check for %s/%s",
                self.scope,
                identifier,
            )
            return

        now = time.time()
        window_bucket = int(now // self.window)
        key = f"rl:{self.scope}:{identifier}:{window_bucket}"

        try:
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.window * 2)
            results: list[Any] = await pipe.execute()
            count: int = int(results[0])
        except Exception as exc:
            logger.warning(
                "Rate limiter Redis error (%s) — skipping check for %s/%s",
                exc,
                self.scope,
                identifier,
            )
            return

        if count > self.limit:
            retry_after = max(1, self.window - int(now) % self.window)
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded ({self.limit} req/{self.window}s). "
                    f"Retry in {retry_after}s."
                ),
                headers={"Retry-After": str(retry_after)},
            )


# ---------------------------------------------------------------------------
# Per-endpoint limiter instances
# ---------------------------------------------------------------------------

_feed_limiter = RateLimiter(limit=30, window=60, scope="feed_read")
_telemetry_limiter = RateLimiter(limit=100, window=60, scope="telemetry")


def _get_redis(request: Request) -> Any:
    return getattr(request.app.state, "redis", None)


# ---------------------------------------------------------------------------
# FastAPI dependency functions — attach via Depends() or dependencies=[...]
# ---------------------------------------------------------------------------


def _make_feed_dep() -> Callable[..., Awaitable[None]]:
    """
    Build the feed rate-limit dependency.

    Declared as a factory so that ``get_current_user_id`` is imported lazily
    (avoids circular-import issues at module load time) yet the returned
    coroutine function carries the ``Depends`` annotation FastAPI needs.
    """
    from auth import get_current_user_id  # lazy import — no circular dep

    async def _feed_rate_limit(
        request: Request,
        current_user_id: int = Depends(get_current_user_id),
    ) -> None:
        await _feed_limiter.check(_get_redis(request), f"user:{current_user_id}")

    return _feed_rate_limit


async def telemetry_rate_limit(request: Request) -> None:
    """100 req/min per client IP — for POST /telemetry."""
    ip = request.client.host if request.client else "unknown"
    await _telemetry_limiter.check(_get_redis(request), f"ip:{ip}")


# Exported dependency — use as  dependencies=[Depends(feed_rate_limit)]
feed_rate_limit: Callable[..., Awaitable[None]] = _make_feed_dep()
