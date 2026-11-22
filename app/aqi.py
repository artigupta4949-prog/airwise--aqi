"""AQI categories and live data lookup (Open-Meteo, no API key needed)."""
from functools import lru_cache

import requests

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEOUT = 6

# (upper bound, key, label) using the US EPA AQI scale
CATEGORIES = [
    (50, "good", "Good"),
    (100, "moderate", "Moderate"),
    (150, "sensitive", "Unhealthy for sensitive groups"),
    (200, "unhealthy", "Unhealthy"),
    (300, "very_unhealthy", "Very unhealthy"),
    (500, "hazardous", "Hazardous"),
]


class AirDataError(RuntimeError):
    """Raised when live air quality data cannot be retrieved."""


def categorize(aqi: int) -> tuple[str, str]:
    for upper, key, label in CATEGORIES:
        if aqi <= upper:
            return key, label
    return CATEGORIES[-1][1], CATEGORIES[-1][2]


@lru_cache(maxsize=256)
def _geocode(city: str) -> tuple[float, float, str]:
    r = requests.get(GEO_URL, params={"name": city, "count": 1}, timeout=TIMEOUT)
    r.raise_for_status()
    results = r.json().get("results") or []
    if not results:
        raise AirDataError("City not found. Check the spelling or enter the AQI manually.")
    top = results[0]
    return top["latitude"], top["longitude"], f'{top["name"]}, {top.get("country", "")}'.strip(", ")


def fetch_air_quality(city: str) -> dict:
    """Return {'aqi', 'pm25', 'place'} for a city."""
    try:
        lat, lon, place = _geocode(city)
        r = requests.get(
            AIR_URL,
            params={"latitude": lat, "longitude": lon, "current": "us_aqi,pm2_5"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        cur = r.json()["current"]
        return {"aqi": round(cur["us_aqi"]), "pm25": cur.get("pm2_5"), "place": place}
    except AirDataError:
        raise
    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        raise AirDataError("Live air data is unavailable. Enter the AQI manually.") from exc
