"""
Shared exponential backoff decorator for all async network calls.

Usage:
    @with_backoff(max_retries=4, exceptions=(httpx.HTTPError,))
    async def fetch_something() -> ...:
        ...
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])
logger = logging.getLogger(__name__)


def with_backoff(
    max_retries: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """
    Async exponential backoff decorator.

    Delay = min(base_delay * 2^attempt + uniform_jitter(0,1), max_delay)

    The jitter term prevents thundering-herd on shared APIs when multiple
    workers retry simultaneously.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: object, **kwargs: object) -> object:
            for attempt in range(max_retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_retries:
                        logger.error(
                            "%s exhausted %d retries: %s",
                            fn.__qualname__,
                            max_retries,
                            exc,
                        )
                        raise
                    delay = min(
                        base_delay * (2**attempt) + random.random(),
                        max_delay,
                    )
                    logger.warning(
                        "%s attempt %d/%d failed (%s). Retry in %.1fs.",
                        fn.__qualname__,
                        attempt + 1,
                        max_retries,
                        type(exc).__name__,
                        delay,
                    )
                    await asyncio.sleep(delay)
            return None  # unreachable but satisfies type checker

        return wrapper  # type: ignore[return-value]

    return decorator
