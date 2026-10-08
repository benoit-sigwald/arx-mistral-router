"""Tests for RateLimiter and backoff calculation."""

import pytest
import asyncio
import time
from arx_router.rate_limiter import FreeTierRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_rps():
    limiter = FreeTierRateLimiter(rps_limit=5.0, tpm_limit=10000, max_concurrent=2)
    t0 = time.time()
    for _ in range(3):
        await limiter.acquire(estimated_tokens=100)
    duration = time.time() - t0
    # 3 requests at 5 RPS should take at least ~0.4s
    assert duration >= 0.35


def test_calculate_backoff():
    # Base backoff
    b0 = FreeTierRateLimiter.calculate_backoff(attempt=0, base_delay=1.0)
    assert 1.0 <= b0 <= 1.6

    b2 = FreeTierRateLimiter.calculate_backoff(attempt=2, base_delay=1.0)
    assert 4.0 <= b2 <= 6.5

    # Respect Retry-After
    b_retry = FreeTierRateLimiter.calculate_backoff(attempt=0, retry_after=5.0)
    assert 5.0 <= b_retry <= 5.6
