"""Rate limiter, concurrency guard, and backoff retry mechanism."""

import asyncio
import random
import time
from collections import deque
from typing import Optional


class FreeTierRateLimiter:
    """
    Enforces free-tier rate limits:
    1. Concurrency limit (Semaphore)
    2. Requests Per Second (RPS) sliding window
    3. Tokens Per Minute (TPM) sliding window
    """

    def __init__(
        self,
        rps_limit: float = 1.0,
        tpm_limit: int = 60000,
        max_concurrent: int = 2,
    ):
        self.rps_limit = rps_limit
        self.min_interval = 1.0 / rps_limit if rps_limit > 0 else 0.0
        self.tpm_limit = tpm_limit
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        self._request_times = deque()
        self._token_records = deque()  # (timestamp, token_count)
        self._lock = asyncio.Lock()
        self._last_request_time = 0.0

    async def acquire(self, estimated_tokens: int = 500) -> None:
        """Wait if necessary to conform to RPS and TPM limits before executing."""
        async with self._lock:
            now = time.time()

            # 1. Clean old entries (> 60 seconds)
            while self._request_times and now - self._request_times[0] > 1.0:
                self._request_times.popleft()

            while self._token_records and now - self._token_records[0][0] > 60.0:
                self._token_records.popleft()

            # 2. Check RPS interval
            elapsed_since_last = now - self._last_request_time
            if elapsed_since_last < self.min_interval:
                delay = self.min_interval - elapsed_since_last
                await asyncio.sleep(delay)
                now = time.time()

            # 3. Check TPM limit
            current_tokens_in_window = sum(t[1] for t in self._token_records)
            if current_tokens_in_window + estimated_tokens > self.tpm_limit:
                # Wait until oldest token record in window expires
                if self._token_records:
                    oldest_time = self._token_records[0][0]
                    wait_time = max(0.1, 60.0 - (now - oldest_time) + 0.1)
                    await asyncio.sleep(wait_time)
                    now = time.time()

            # 4. Record new request
            self._request_times.append(now)
            self._token_records.append((now, estimated_tokens))
            self._last_request_time = now

    @staticmethod
    def calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 20.0, retry_after: Optional[float] = None) -> float:
        """Calculate exponential backoff with jitter, or respect Retry-After."""
        if retry_after is not None and retry_after > 0:
            # Add minor jitter to retry_after
            return retry_after + random.uniform(0.1, 0.5)
        
        delay = min(max_delay, base_delay * (2 ** attempt))
        jitter = random.uniform(0.0, 0.5 * delay)
        return delay + jitter
