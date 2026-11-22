"""HTTP routes."""
from flask import Blueprint, current_app, jsonify, render_template, request

from . import aqi as aqi_mod
from .advisor import build_advice
from .llm import personalize
from .validation import ValidationError, parse_profile

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/healthz")
def healthz():
    return jsonify(status="ok")


@bp.post("/api/advice")
def advice():
    limiter = current_app.extensions["limiter"]
    if not limiter.allow(request.remote_addr or "unknown"):
        return jsonify(error="Too many requests. Please wait a minute."), 429

    try:
        profile = parse_profile(request.get_json(silent=True))
    except ValidationError as exc:
        return jsonify(error=str(exc)), 400

    place, pm25 = profile.city, None
    if profile.manual_aqi is not None:
        value = profile.manual_aqi
    else:
        try:
            reading = aqi_mod.fetch_air_quality(profile.city)
        except aqi_mod.AirDataError as exc:
            return jsonify(error=str(exc)), 502
        value, place, pm25 = reading["aqi"], reading["place"], reading["pm25"]

    result = build_advice(profile, value)
    result.update(
        place=place,
        pm25=pm25,
        data_source="Manual AQI" if profile.manual_aqi is not None else "Open-Meteo",
        narrative=personalize(profile, result, place),
        disclaimer="Impact estimates are directional, not medical measurements.",
    )
    return jsonify(result)
