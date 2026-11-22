import pytest

from app.validation import ValidationError, parse_profile

VALID = {"city": "Delhi", "home": "house", "commute": "car", "heating": "gas", "groups": ["asthma"]}


def test_valid_profile():
    p = parse_profile(VALID)
    assert p.city == "Delhi" and p.groups == ("asthma",) and p.manual_aqi is None


@pytest.mark.parametrize("bad", [
    {**VALID, "city": ""},
    {**VALID, "city": "<script>alert(1)</script>"},
    {**VALID, "home": "castle"},
    {**VALID, "groups": ["aliens"]},
    {**VALID, "groups": "children"},
    {**VALID, "manual_aqi": "abc"},
    {**VALID, "manual_aqi": 501},
    {**VALID, "manual_aqi": -1},
    ["not", "a", "dict"],
])
def test_rejects_bad_input(bad):
    with pytest.raises(ValidationError):
        parse_profile(bad)


def test_groups_deduplicated_and_sorted():
    p = parse_profile({**VALID, "groups": ["elderly", "children", "children"]})
    assert p.groups == ("children", "elderly")


def test_manual_aqi_accepts_numeric_string_and_blank():
    assert parse_profile({**VALID, "manual_aqi": "150"}).manual_aqi == 150
    assert parse_profile({**VALID, "manual_aqi": ""}).manual_aqi is None


def test_defaults_applied_for_optional_fields():
    p = parse_profile({"city": "Delhi"})
    assert (p.home, p.commute, p.heating, p.groups) == ("apartment", "public", "none", ())
