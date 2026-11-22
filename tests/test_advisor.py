import pytest

from app.advisor import build_advice
from app.aqi import categorize
from app.validation import parse_profile


def profile(**kw):
    return parse_profile({"city": "Delhi", **kw})


@pytest.mark.parametrize("aqi,key", [
    (0, "good"), (50, "good"), (51, "moderate"), (150, "sensitive"),
    (151, "unhealthy"), (300, "very_unhealthy"), (301, "hazardous"), (999, "hazardous"),
])
def test_categorize(aqi, key):
    assert categorize(aqi)[0] == key


def test_clean_air_has_no_mask_advice():
    advice = build_advice(profile(commute="walk"), 30)
    titles = " ".join(a["title"] for a in advice["routines"])
    assert "N95" not in titles
    assert "Normal outdoor activity" in titles


def test_severe_smog_moves_exercise_indoors():
    advice = build_advice(profile(), 220)
    assert any("indoors" in a["title"] for a in advice["routines"])


def test_cyclist_gets_mask_in_poor_air():
    advice = build_advice(profile(commute="cycle"), 160)
    assert any("N95" in a["title"] for a in advice["routines"])


def test_wood_heating_gets_alternative():
    advice = build_advice(profile(heating="wood_coal"), 120)
    assert any("electric heater" in a["title"] for a in advice["alternatives"])


def test_vulnerable_household_noted():
    advice = build_advice(profile(groups=["children"]), 160)
    assert "higher risk" in advice["summary"]


def test_every_action_explains_impact():
    advice = build_advice(profile(commute="car", heating="wood_coal", groups=["asthma"]), 180)
    for section in ("routines", "indoor", "alternatives"):
        assert advice[section]
        assert all(a["title"] and a["why"] and a["impact"] for a in advice[section])


@pytest.mark.parametrize("aqi", [0, 50, 100, 150, 200, 300, 500])
def test_all_supported_aqi_levels_return_complete_plan(aqi):
    advice = build_advice(profile(groups=["children", "pregnant"], commute="two_wheeler",
                                 heating="gas"), aqi)
    assert advice["aqi"] == aqi
    assert advice["summary"]
    assert advice["routines"] and advice["indoor"] and advice["alternatives"]


def test_moderate_air_keeps_outdoor_advice_light():
    advice = build_advice(profile(), 80)
    assert "Normal outdoor activity" in advice["routines"][0]["title"]
    assert "Unusually sensitive" in advice["summary"]


def test_boundary_at_poor_threshold():
    assert "Keep outdoor activity short" in build_advice(profile(), 101)["routines"][0]["title"]
    assert "Normal outdoor" in build_advice(profile(), 100)["routines"][0]["title"]


def test_car_commuter_gets_recirculation_advice():
    advice = build_advice(profile(commute="car"), 160)
    assert any("recirculation" in a["title"] for a in advice["routines"])
