"""Input validation. Everything from the client passes through here."""
import re
from dataclasses import dataclass

HOME_TYPES = {"apartment", "house", "shared"}
COMMUTES = {"walk", "cycle", "public", "two_wheeler", "car", "remote"}
GROUPS = {"children", "elderly", "asthma", "pregnant"}
HEATING = {"electric", "gas", "wood_coal", "none"}
_CITY_RE = re.compile(r"^[\w .,'\-]{2,80}$", re.UNICODE)


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Profile:
    city: str
    home: str
    commute: str
    heating: str
    groups: tuple[str, ...]
    manual_aqi: int | None


def _choice(data: dict, key: str, allowed: set, default: str) -> str:
    value = data.get(key, default)
    if value not in allowed:
        raise ValidationError(f"Invalid value for {key}.")
    return value


def parse_profile(data) -> Profile:
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    city = str(data.get("city", "")).strip()
    if not _CITY_RE.match(city):
        raise ValidationError("Enter a city name of 2 to 80 letters.")

    groups = data.get("groups", [])
    if not isinstance(groups, list) or not all(isinstance(g, str) for g in groups) or not set(groups) <= GROUPS:
        raise ValidationError("Invalid household groups.")

    manual = data.get("manual_aqi")
    if manual in (None, ""):
        manual_aqi = None
    else:
        try:
            manual_aqi = int(manual)
        except (TypeError, ValueError):
            raise ValidationError("AQI must be a whole number.") from None
        if not 0 <= manual_aqi <= 500:
            raise ValidationError("AQI must be between 0 and 500.")

    return Profile(
        city=city,
        home=_choice(data, "home", HOME_TYPES, "apartment"),
        commute=_choice(data, "commute", COMMUTES, "public"),
        heating=_choice(data, "heating", HEATING, "none"),
        groups=tuple(sorted(set(groups))),
        manual_aqi=manual_aqi,
    )
