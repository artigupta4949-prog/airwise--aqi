from app.llm import personalize
from app.validation import parse_profile


def test_personalization_is_skipped_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    profile = parse_profile({"city": "Delhi"})
    advice = {
        "aqi": 180,
        "label": "Unhealthy",
        "routines": [{"title": "Keep outdoor activity short"}],
        "indoor": [{"title": "Use a HEPA purifier"}],
    }

    assert personalize(profile, advice, "Delhi, India") is None
