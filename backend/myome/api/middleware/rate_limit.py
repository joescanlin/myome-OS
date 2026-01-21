"""Rate limiting middleware"""

import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self._minute_counts: dict[str, list[float]] = defaultdict(list)
        self._hour_counts: dict[str, list[float]] = defaultdict(list)

    def _clean_old_requests(
        self, key: str, window_seconds: int, storage: dict[str, list[float]]
    ) -> None:
        """Remove requests older than window"""
        now = time.time()
        storage[key] = [ts for ts in storage[key] if now - ts < window_seconds]

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed"""
        now = time.time()

        # Clean old entries
        self._clean_old_requests(client_id, 60, self._minute_counts)
        self._clean_old_requests(client_id, 3600, self._hour_counts)

        # Check limits
        if len(self._minute_counts[client_id]) >= self.rpm:
            return False
        if len(self._hour_counts[client_id]) >= self.rph:
            return False

        # Record request
        self._minute_counts[client_id].append(now)
        self._hour_counts[client_id].append(now)

        return True

    def get_retry_after(self, client_id: str) -> int:
        """Get seconds until next allowed request"""
        if self._minute_counts[client_id]:
            oldest = min(self._minute_counts[client_id])
            return max(0, int(60 - (time.time() - oldest)))
        return 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI"""

    def __init__(self, app, limiter: RateLimiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: Callable):
        # Get client identifier (IP or user ID from token)
        client_id = request.client.host if request.client else "unknown"

        # Check rate limit
        if not self.limiter.is_allowed(client_id):
            retry_after = self.limiter.get_retry_after(client_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
