"""
Tests for src/retry.py — exponential backoff decorator.
Uses asyncio mocking to keep tests fast (no real sleeps).
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.retry import with_backoff


class TestWithBackoff:
    async def test_succeeds_on_first_try(self) -> None:
        call_count = 0

        @with_backoff(max_retries=3)
        async def succeed_immediately() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        with patch("src.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await succeed_immediately()

        assert result == "ok"
        assert call_count == 1

    async def test_retries_on_failure_then_succeeds(self) -> None:
        call_count = 0

        @with_backoff(max_retries=3)
        async def fail_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient failure")
            return "recovered"

        with patch("src.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await fail_twice()

        assert result == "recovered"
        assert call_count == 3

    async def test_raises_after_max_retries_exhausted(self) -> None:
        call_count = 0

        @with_backoff(max_retries=2)
        async def always_fail() -> None:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("always fails")

        with patch("src.retry.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="always fails"):
                await always_fail()

        # max_retries=2 means 3 total attempts (attempt 0, 1, 2)
        assert call_count == 3

    async def test_sleep_is_called_between_retries(self) -> None:
        @with_backoff(max_retries=2, base_delay=1.0)
        async def always_fail() -> None:
            raise RuntimeError("fail")

        mock_sleep = AsyncMock()
        with patch("src.retry.asyncio.sleep", mock_sleep):
            with pytest.raises(RuntimeError):
                await always_fail()

        # Should have slept twice (before attempt 1 and attempt 2)
        assert mock_sleep.call_count == 2

    async def test_delay_increases_exponentially(self) -> None:
        """First delay ≈ base_delay, second delay ≈ 2 * base_delay (before jitter)."""
        calls: list[float] = []

        @with_backoff(max_retries=3, base_delay=2.0, max_delay=100.0)
        async def always_fail() -> None:
            raise ValueError("fail")

        async def capture_sleep(delay: float) -> None:
            calls.append(delay)

        with patch("src.retry.asyncio.sleep", side_effect=capture_sleep):
            with pytest.raises(ValueError):
                await always_fail()

        # Delays: attempt 0 → base*2^0 + jitter, attempt 1 → base*2^1 + jitter, etc.
        # Without jitter the floor values are 2.0, 4.0, 8.0
        # With jitter (0–1): min possible is 2.0, 4.0, 8.0
        assert len(calls) == 3
        assert calls[0] >= 2.0
        assert calls[1] >= 4.0

    async def test_max_delay_is_respected(self) -> None:
        """Delay should never exceed max_delay."""
        delays: list[float] = []

        @with_backoff(max_retries=10, base_delay=30.0, max_delay=60.0)
        async def always_fail() -> None:
            raise ValueError("fail")

        async def capture(delay: float) -> None:
            delays.append(delay)

        with patch("src.retry.asyncio.sleep", side_effect=capture):
            with pytest.raises(ValueError):
                await always_fail()

        assert all(d <= 60.0 for d in delays)

    async def test_only_specified_exceptions_trigger_retry(self) -> None:
        call_count = 0

        @with_backoff(max_retries=3, exceptions=(ValueError,))
        async def raises_type_error() -> None:
            nonlocal call_count
            call_count += 1
            raise TypeError("not retried")

        with patch("src.retry.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(TypeError):
                await raises_type_error()

        # TypeError not in exceptions tuple — should propagate immediately
        assert call_count == 1

    async def test_zero_max_retries_raises_immediately(self) -> None:
        call_count = 0

        @with_backoff(max_retries=0)
        async def fail() -> None:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("immediate")

        with patch("src.retry.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError):
                await fail()

        assert call_count == 1
