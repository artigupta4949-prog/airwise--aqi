"""Application configuration and tunable constants."""
from __future__ import annotations

import os

DEFAULTS: dict[str, object] = {
    "MAX_CONTENT_LENGTH": 8 * 1024,  # requests are tiny; reject anything larger
    "RATE_LIMIT": 20,
    "RATE_WINDOW_SECONDS": 60,
    "AIR_CACHE_SECONDS": 600,
    "SEND_FILE_MAX_AGE_DEFAULT": 3600,
    "JSON_SORT_KEYS": False,
    # Set TRUST_PROXY=1 behind a single reverse proxy (Cloud Run, Vercel) so the
    # rate limiter sees real client addresses instead of the proxy's.
    "TRUST_PROXY": os.environ.get("TRUST_PROXY", "") == "1",
}
