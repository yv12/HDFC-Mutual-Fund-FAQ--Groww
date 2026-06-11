"""
In-memory rate limiter for FastAPI endpoints.

Tracks client request timestamps in memory to enforce settings-defined limits
without introducing external database dependencies like Redis.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from fastapi import HTTPException, Request, status

from app.config import settings

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Sliding window rate limiter stored in-memory."""

    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        # Dict mapping IP strings to list of epoch timestamps
        self.history: dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(self, client_ip: str) -> bool:
        """
        Check if the request from client_ip is within the rate limit.

        Returns:
            True if request is allowed, False if rate limited.
        """
        now = time.time()
        # Filter out timestamps older than the window duration
        self.history[client_ip] = [
            t for t in self.history[client_ip] if now - t < self.window_seconds
        ]

        if len(self.history[client_ip]) >= self.limit:
            logger.warning(
                "Rate Limit Exceeded: IP %s requested %d times in last %d seconds.",
                client_ip,
                len(self.history[client_ip]),
                self.window_seconds,
            )
            return False

        self.history[client_ip].append(now)
        return True


# Instantiate global rate limiter using settings
limiter = InMemoryRateLimiter(limit=settings.rate_limit_per_minute)


async def rate_limit_dependency(request: Request) -> None:
    """
    FastAPI dependency to enforce client-IP rate limiting.

    Raises:
        HTTPException with status code 429 when rate limit is exceeded.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    if not limiter.check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )
