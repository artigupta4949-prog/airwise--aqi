"""HTTP routes."""
from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, render_template, request

from . import aqi as aqi_mod
from .advisor import build_advice
from .llm import personalize
from .validation import Profile, ValidationError, parse_profile

bp = Blueprint("main", __name__)

DISCLAIMER = "Impact estimates are directional, not medical measurements."


@bp.get("/")
def index() -> str:
    return render_template("index.html")


@bp.get("/healthz")
def healthz() -> Response:
    return jsonify(status="ok")


def _resolve_reading(profile: Profile) -> tuple[aqi_mod.AirReading, str]:
    """Return the AQI reading and its data-source label (manual input or live lookup)."""
    if profile.manual_aqi is not None:
        return aqi_mod.AirReading(profile.manual_aqi, None, profile.city), "Manual AQI"
    reading = aqi_mod.fetch_air_quality(
        profile.city, current_app.config["AIR_CACHE_SECONDS"]
    )
    return reading, "Open-Meteo"


@bp.post("/api/advice")
def advice() -> tuple[Response, int] | Response:
    limiter = current_app.extensions["limiter"]
    if not limiter.allow(request.remote_addr or "unknown"):
        return jsonify(error="Too many requests. Please wait a minute."), 429

    try:
        profile = parse_profile(request.get_json(silent=True))
        reading, source = _resolve_reading(profile)
    except ValidationError as exc:
        return jsonify(error=str(exc)), 400
    except aqi_mod.AirDataError as exc:
        return jsonify(error=str(exc)), 502

    result = build_advice(profile, reading.aqi)
    result.update(
        place=reading.place,
        pm25=reading.pm25,
        data_source=source,
        narrative=personalize(profile, result, reading.place),
        disclaimer=DISCLAIMER,
    )
    return jsonify(result)
