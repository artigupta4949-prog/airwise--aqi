from app import aqi as aqi_mod
from app import create_app
from app.aqi import AirReading

BODY = {"city": "Delhi", "manual_aqi": 180, "commute": "cycle"}


def test_index_is_accessible_html(client):
    html = client.get("/").get_data(as_text=True)
    assert '<html lang="en">' in html
    assert 'class="skip"' in html
    assert 'for="city"' in html
    assert 'aria-live="polite"' in html
    assert 'role="img"' in html


def test_security_headers(client):
    res = client.get("/")
    assert "default-src 'self'" in res.headers["Content-Security-Policy"]
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_page_explains_problem_and_solution(client):
    html = client.get("/").get_data(as_text=True)
    assert "A plan for your household" in html
    assert "Air pollution affects people differently" in html
    assert 'id="data-source"' in html


def test_advice_with_manual_aqi(client):
    res = client.post("/api/advice", json=BODY)
    data = res.get_json()
    assert res.status_code == 200
    assert data["category"] == "unhealthy" and data["routines"]
    assert data["data_source"] == "Manual AQI"
    assert "directional" in data["disclaimer"]


def test_advice_rejects_bad_input(client):
    assert client.post("/api/advice", json={"city": "x"}).status_code == 400
    assert client.post("/api/advice", data="nope", content_type="text/plain").status_code == 400


def test_live_lookup_used_when_no_manual_aqi(client, monkeypatch):
    monkeypatch.setattr(aqi_mod, "fetch_air_quality",
                        lambda city, cache_seconds=0: AirReading(40, 9.0, "Testville, IN"))
    data = client.post("/api/advice", json={"city": "Testville"}).get_json()
    assert data["aqi"] == 40 and data["place"] == "Testville, IN"
    assert data["data_source"] == "Open-Meteo"


def test_lookup_failure_returns_502(client, monkeypatch):
    def boom(city, cache_seconds=0):
        raise aqi_mod.AirDataError("down")
    monkeypatch.setattr(aqi_mod, "fetch_air_quality", boom)
    assert client.post("/api/advice", json={"city": "Delhi"}).status_code == 502


def test_oversized_body_rejected(client):
    res = client.post("/api/advice", json={"city": "Delhi", "pad": "x" * 20000})
    assert res.status_code == 413


def test_rate_limit():
    c = create_app({"TESTING": True, "RATE_LIMIT": 2}).test_client()
    codes = [c.post("/api/advice", json=BODY).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_static_assets_are_served_and_linked(client):
    html = client.get("/").get_data(as_text=True)
    for path in ("/static/style.css", "/static/app.js"):
        assert path in html
        assert client.get(path).status_code == 200


def test_api_errors_are_json(client):
    res = client.get("/api/advice")
    assert res.status_code == 405
    assert res.get_json() == {"error": "Method not allowed."}
    assert client.get("/api/missing").get_json() == {"error": "Not found."}


def test_api_responses_are_not_cached(client):
    res = client.post("/api/advice", json=BODY)
    assert res.headers["Cache-Control"] == "no-store"


def test_hardening_headers_present(client):
    headers = client.get("/").headers
    for name in ("Strict-Transport-Security", "Cross-Origin-Opener-Policy",
                 "Cross-Origin-Resource-Policy", "Permissions-Policy"):
        assert name in headers


def test_advice_includes_gauge_position(client):
    data = client.post("/api/advice", json=BODY).get_json()
    assert 0 <= data["gauge_position"] <= 100


def test_proxy_header_trusted_only_when_enabled():
    app = create_app({"TESTING": True, "TRUST_PROXY": True, "RATE_LIMIT": 1})
    c = app.test_client()
    ok = c.post("/api/advice", json=BODY, headers={"X-Forwarded-For": "1.1.1.1"})
    other = c.post("/api/advice", json=BODY, headers={"X-Forwarded-For": "2.2.2.2"})
    assert ok.status_code == other.status_code == 200


def test_non_api_404_is_not_json(client):
    assert client.get("/nope").status_code == 404


def test_unexpected_api_error_is_json(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.routes.build_advice", boom)
    res = client.post("/api/advice", json=BODY)
    assert res.status_code == 500
    assert res.get_json() == {"error": "An unexpected error occurred."}
