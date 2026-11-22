"""Security helpers: response headers and a small in-memory rate limiter."""
from __future__ import annotations

import time
from collections import deque
from threading import Lock

from flask import Response, request

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
    "form-action 'self'"
)

_STATIC_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


def apply_security_headers(response: Response) -> Response:
    """Attach hardening headers to every response; never cache API output."""
    response.headers.update(_STATIC_HEADERS)
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


class RateLimiter:
    """Sliding-window limiter keyed by client address."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """Record a hit for ``key`` and return whether it is within the limit."""
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            hits = self._hits.setdefault(key, deque())
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def _prune(self, now: float) -> None:
        """Drop expired hits and idle keys so memory stays bounded."""
        for key in list(self._hits):
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if not hits:
                del self._hits[key]
