"""
Authentication and rate limiting utilities for EthixAI API.

This module defines a reusable dependency to verify API keys passed in via
the ``x-api-key`` header and a simple rate limiting middleware to guard
against abusive clients. The rate limiter uses a sliding window based on
timestamps stored in memory, and applies a global limit across all
requests. For a production deployment, consider a more robust rate
limiting solution (e.g., Redis-backed) instead of in-memory storage.
"""

from __future__ import annotations

import os
import time
from collections import deque
from typing import Callable

from fastapi import Header, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Dependency that verifies an incoming request carries the correct API key.

    Args:
        x_api_key: The API key sent in the ``x-api-key`` header.

    Raises:
        HTTPException: If the header is missing or does not match the expected key.
    """
    expected_key = os.getenv("API_KEY")
    if expected_key is None:
        # If no key is configured, all keys are considered invalid.
        raise HTTPException(status_code=500, detail="Server misconfigured: API_KEY not set")
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter middleware for FastAPI/Starlette.

    This middleware limits incoming requests to a specified maximum number
    within a time window. It uses a deque to store timestamps of recent
    requests and enforces a global rate limit across all clients. If the
    incoming request rate exceeds the configured threshold, the middleware
    responds with HTTP 429 (Too Many Requests).
    """

    def __init__(self, app: Callable, max_requests: int = 10, window_seconds: float = 1.0) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._request_times: deque[float] = deque()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        current_time = time.monotonic()
        # Remove timestamps outside the sliding window
        while self._request_times and current_time - self._request_times[0] > self.window_seconds:
            self._request_times.popleft()
        if len(self._request_times) >= self.max_requests:
            # Too many requests in the window
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        self._request_times.append(current_time)
        return await call_next(request)
