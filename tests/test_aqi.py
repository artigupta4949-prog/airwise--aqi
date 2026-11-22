import pytest
import requests

from app import aqi
from app.aqi import AirDataError, AirReading, gauge_position


@pytest.fixture(autouse=True)
def clear_caches():
    aqi._geocode.cache_clear()
    aqi._cache.clear()
    yield


class FakeResponse:
    def __init__(self, payload, error=None):
        self._payload, self._error = payload, error

    def raise_for_status(self):
        if self._error:
            raise self._error

    def json(self):
        return self._payload


def fake_get(calls=None, geo=None, air=None):
    geo = geo if geo is not None else {"results": [
        {"name": "Delhi", "country": "India", "latitude": 28.6, "longitude": 77.2}]}
    air = air if air is not None else {"current": {"us_aqi": 182.4, "pm2_5": 95.1}}

    def get(url, params=None, timeout=None):
        if calls is not None:
            calls.append(url)
        return FakeResponse(geo if url == aqi.GEO_URL else air)

    return get


def test_fetch_returns_reading(monkeypatch):
    monkeypatch.setattr(aqi.requests, "get", fake_get())
    assert aqi.fetch_air_quality("Delhi") == AirReading(182, 95.1, "Delhi, India")


def test_reading_is_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(aqi.requests, "get", fake_get(calls))
    aqi.fetch_air_quality("Delhi")
    aqi.fetch_air_quality("delhi")
    assert len(calls) == 2  # one geocode + one air call, second lookup served from cache


def test_cache_can_be_bypassed(monkeypatch):
    calls = []
    monkeypatch.setattr(aqi.requests, "get", fake_get(calls))
    aqi.fetch_air_quality("Delhi", cache_seconds=0)
    aqi.fetch_air_quality("Delhi", cache_seconds=0)
    assert calls.count(aqi.AIR_URL) == 2


def test_unknown_city(monkeypatch):
    monkeypatch.setattr(aqi.requests, "get", fake_get(geo={"results": []}))
    with pytest.raises(AirDataError, match="City not found"):
        aqi.fetch_air_quality("Nowhereville")


def test_network_failure_becomes_air_data_error(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(aqi.requests, "get", boom)
    with pytest.raises(AirDataError, match="unavailable"):
        aqi.fetch_air_quality("Delhi")


def test_missing_aqi_field_becomes_air_data_error(monkeypatch):
    monkeypatch.setattr(aqi.requests, "get", fake_get(air={"current": {"us_aqi": None}}))
    with pytest.raises(AirDataError):
        aqi.fetch_air_quality("Delhi")


def test_cache_is_bounded(monkeypatch):
    monkeypatch.setattr(aqi.requests, "get", fake_get())
    monkeypatch.setattr(aqi, "_READING_CACHE_SIZE", 2)
    for city in ("aa", "bb", "cc"):
        aqi.fetch_air_quality(city)
    assert len(aqi._cache) == 2


@pytest.mark.parametrize("value,expected", [(0, 0.0), (50, 16.7), (500, 100.0), (999, 100.0)])
def test_gauge_position(value, expected):
    assert gauge_position(value) == expected


def test_gauge_position_is_monotonic():
    positions = [gauge_position(v) for v in range(0, 501, 10)]
    assert positions == sorted(positions)


def test_gauge_position_is_clamped():
    assert gauge_position(-10) == 0.0
    assert gauge_position(999) == 100.0


def test_live_reading_clamps_aqi_and_normalises_pm25(monkeypatch):
    monkeypatch.setattr(aqi.requests, "get", fake_get(
        air={"current": {"us_aqi": 999.4, "pm2_5": -4.2}}
    ))
    reading = aqi.fetch_air_quality("Delhi")
    assert reading.aqi == 500
    assert reading.pm25 == 0.0


@pytest.mark.parametrize("pm25", [None, "unknown", float("nan")])
def test_live_reading_accepts_missing_or_invalid_pm25(monkeypatch, pm25):
    monkeypatch.setattr(aqi.requests, "get", fake_get(
        air={"current": {"us_aqi": 182, "pm2_5": pm25}}
    ))
    assert aqi.fetch_air_quality("Delhi").pm25 is None
