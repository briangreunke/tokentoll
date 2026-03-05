from __future__ import annotations

from collections import defaultdict
from time import time

from fastapi import HTTPException, Request

from tokentoll.config import get_settings


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter for async usage."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._requests[key] = [
            timestamp
            for timestamp in self._requests[key]
            if timestamp > cutoff
        ]

    def is_allowed(self, key: str) -> bool:
        now = time()
        self._prune(key, now)
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time()
        self._prune(key, now)
        remaining = self.max_requests - len(self._requests[key])
        return max(remaining, 0)

    def reset_time(self, key: str) -> float:
        now = time()
        self._prune(key, now)
        if not self._requests[key]:
            return 0.0
        oldest = self._requests[key][0]
        reset = (oldest + self.window_seconds) - now
        return max(reset, 0.0)


settings = get_settings()
challenge_rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.challenge_rate_limit_per_minute,
    window_seconds=settings.challenge_rate_limit_window_seconds,
)


async def check_rate_limit(request: Request) -> None:
    ip_address = request.client.host if request.client else "unknown"
    if not challenge_rate_limiter.is_allowed(ip_address):
        remaining = challenge_rate_limiter.remaining(ip_address)
        reset = challenge_rate_limiter.reset_time(ip_address)
        raise HTTPException(
            status_code=429,
            detail={"error": "rate_limit_exceeded"},
            headers={
                "Retry-After": str(int(reset)),
                "X-RateLimit-Remaining": str(remaining),
            },
        )
