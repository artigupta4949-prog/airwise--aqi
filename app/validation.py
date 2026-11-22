"""Input validation. Everything from the client passes through here."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

HOME_TYPES = frozenset({"apartment", "house", "shared"})
COMMUTES = frozenset({"walk", "cycle", "public", "two_wheeler", "car", "remote"})
GROUPS = frozenset({"children", "elderly", "asthma", "pregnant"})
HEATING = frozenset({"electric", "gas", "wood_coal", "none"})
AQI_MIN, AQI_MAX = 0, 500
_CITY_RE = re.compile(r"^[\w .,'\-]{2,80}$", re.UNICODE)


class ValidationError(ValueError):
    """Raised when client input is malformed or outside the allowed values."""


@dataclass(frozen=True)
class Profile:
    """A validated household profile."""

    city: str
    home: str
    commute: str
    heating: str
    groups: tuple[str, ...]
    manual_aqi: int | None


def _choice(data: dict[str, Any], key: str, allowed: frozenset[str], default: str) -> str:
    value = data.get(key, default)
    if value not in allowed:
        raise ValidationError(f"Invalid value for {key}.")
    return value


def _parse_groups(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list) or not all(isinstance(g, str) for g in raw) or not set(raw) <= GROUPS:
        raise ValidationError("Invalid household groups.")
    return tuple(sorted(set(raw)))


def _parse_manual_aqi(raw: Any) -> int | None:
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError("AQI must be a whole number.") from None
    if not AQI_MIN <= value <= AQI_MAX:
        raise ValidationError(f"AQI must be between {AQI_MIN} and {AQI_MAX}.")
    return value


def parse_profile(data: Any) -> Profile:
    """Validate raw request JSON and return a Profile, or raise ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    city = str(data.get("city", "")).strip()
    if not _CITY_RE.match(city):
        raise ValidationError("Enter a city name of 2 to 80 letters.")

    return Profile(
        city=city,
        home=_choice(data, "home", HOME_TYPES, "apartment"),
        commute=_choice(data, "commute", COMMUTES, "public"),
        heating=_choice(data, "heating", HEATING, "none"),
        groups=_parse_groups(data.get("groups", [])),
        manual_aqi=_parse_manual_aqi(data.get("manual_aqi")),
    )
