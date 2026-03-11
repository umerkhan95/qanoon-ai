"""Rate limiter for court website crawlers.

Single responsibility: enforce request rate limits with backoff.
Thread-safe, configurable per-domain. Prevents IP bans from court servers.
"""

from __future__ import annotations

import logging
import time
import threading

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter.

    Args:
        requests_per_second: Maximum requests per second.
        burst: Maximum burst size (defaults to requests_per_second).

    Usage:
        limiter = RateLimiter(requests_per_second=2.0)
        for url in urls:
            limiter.wait()  # blocks until a request is allowed
            response = await fetch(url)
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        burst: int | None = None,
    ) -> None:
        if requests_per_second <= 0:
            raise ValueError(f"requests_per_second must be positive, got {requests_per_second}")
        self.rate = requests_per_second
        self.burst = burst or max(1, int(requests_per_second))
        self._tokens = float(self.burst)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._request_count = 0

    def wait(self) -> None:
        """Block until a request token is available."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    self._request_count += 1
                    return

            # Sleep for the time needed to get one token
            time.sleep(1.0 / self.rate)

    def _refill(self) -> None:
        """Add tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            float(self.burst),
            self._tokens + elapsed * self.rate,
        )
        self._last_refill = now

    @property
    def request_count(self) -> int:
        """Total requests made through this limiter."""
        return self._request_count


def backoff_wait(
    attempt: int,
    base_seconds: float = 1.0,
    max_seconds: float = 60.0,
) -> None:
    """Exponential backoff sleep for retry logic.

    Args:
        attempt: Current attempt number (1-based).
        base_seconds: Base wait time.
        max_seconds: Maximum wait time cap.
    """
    wait = min(base_seconds * (2 ** (attempt - 1)), max_seconds)
    logger.info("Backoff: waiting %.1fs (attempt %d)", wait, attempt)
    time.sleep(wait)
