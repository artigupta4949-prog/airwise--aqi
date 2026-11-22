"""AQI categories and live data lookup (Open-Meteo, no API key needed)."""
from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock

import requests

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEOUT_SECONDS = 6
CACHE_SECONDS = 600
_GEOCODE_CACHE_SIZE = 256
_READING_CACHE_SIZE = 256

# (upper bound, key, label) using the US EPA AQI scale
CATEGORIES: tuple[tuple[int, str, str], ...] = (
    (50, "good", "Good"),
    (100, "moderate", "Moderate"),
    (150, "sensitive", "Unhealthy for sensitive groups"),
    (200, "unhealthy", "Unhealthy"),
    (300, "very_unhealthy", "Very unhealthy"),
    (500, "hazardous", "Hazardous"),
)


class AirDataError(RuntimeError):
    """Raised when live air quality data cannot be retrieved."""


@dataclass(frozen=True)
class AirReading:
    """A live air quality observation."""

    aqi: int
    pm25: float | None
    place: str


def categorize(aqi: int) -> tuple[str, str]:
    """Map an AQI value to its (key, label) EPA category."""
    for upper, key, label in CATEGORIES:
        if aqi <= upper:
            return key, label
    return CATEGORIES[-1][1], CATEGORIES[-1][2]


def gauge_position(aqi: int) -> float:
    """Return 0-100: where an AQI sits on a gauge of equal-width category segments."""
    segment = 100 / len(CATEGORIES)
    lower = 0
    for index, (upper, _, _) in enumerate(CATEGORIES):
        if aqi <= upper:
            return round(index * segment + (aqi - lower) / (upper - lower) * segment, 1)
        lower = upper
    return 100.0


@lru_cache(maxsize=_GEOCODE_CACHE_SIZE)
def _geocode(city: str) -> tuple[float, float, str]:
    params: dict[str, str | int | float] = {"name": city, "count": 1}
    response = requests.get(GEO_URL, params=params, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        raise AirDataError("City not found. Check the spelling or enter the AQI manually.")
    top = results[0]
    place = ", ".join(part for part in (top["name"], top.get("country")) if part)
    return top["latitude"], top["longitude"], place


_cache: dict[str, tuple[float, AirReading]] = {}
_cache_lock = Lock()


def fetch_air_quality(city: str, cache_seconds: int = CACHE_SECONDS) -> AirReading:
    """Return the current reading for ``city``, cached briefly to spare the upstream API."""
    key = city.casefold()
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(key)
        if cached and now - cached[0] < cache_seconds:
            return cached[1]

    reading = _fetch_uncached(city)
    with _cache_lock:
        if len(_cache) >= _READING_CACHE_SIZE:
            _cache.pop(min(_cache, key=lambda k: _cache[k][0]))
        _cache[key] = (now, reading)
    return reading


def _fetch_uncached(city: str) -> AirReading:
    try:
        lat, lon, place = _geocode(city)
        params: dict[str, str | int | float] = {
            "latitude": lat, "longitude": lon, "current": "us_aqi,pm2_5",
        }
        response = requests.get(AIR_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        current = response.json()["current"]
        return AirReading(
            aqi=round(current["us_aqi"]), pm25=current.get("pm2_5"), place=place
        )
    except AirDataError:
        raise
    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        raise AirDataError("Live air data is unavailable. Enter the AQI manually.") from exc
