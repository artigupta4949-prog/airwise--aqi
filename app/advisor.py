"""Deterministic advice engine. Works offline and grounds the GenAI layer.

Each action carries an estimated exposure impact so users see why it matters.
Impact figures are rough, directional estimates, not medical measurements.
"""
from __future__ import annotations

from .aqi import categorize, gauge_position
from .validation import Profile

# AQI thresholds that change the advice (US EPA scale).
GOOD_MAX = 50
POOR_ABOVE = 100  # above this, sensitive people and everyone outdoors feel it
SEVERE_ABOVE = 150
OPEN_AIR_COMMUTES = frozenset({"walk", "cycle", "two_wheeler"})
COMBUSTION_HEATING = frozenset({"wood_coal", "gas"})


def _action(title: str, why: str, impact: str) -> dict[str, str]:
    return {"title": title, "why": why, "impact": impact}


def _routines(profile: Profile, aqi: int) -> list[dict[str, str]]:
    poor, severe = aqi > POOR_ABOVE, aqi > SEVERE_ABOVE
    out = []
    if severe:
        out += [
            _action("Move outdoor exercise and school play indoors",
                    "Breathing rate rises during exercise, so you inhale far more fine particles.",
                    "Removes the outdoor share of that activity's exposure."),
            _action("Go out in the afternoon, not early morning",
                    "Winter inversions trap smog near the ground until the sun warms the air.",
                    "Pollutant levels are often noticeably lower after midday."),
        ]
    elif poor:
        out.append(_action("Keep outdoor activity short and low-intensity",
                           "Light activity limits how deeply you breathe in particles.",
                           "Lowers the dose you take in per hour outside."))
    else:
        out.append(_action("Normal outdoor activity is fine today",
                           "Air quality is within a safe range for most people.",
                           "No extra exposure reduction needed."))
    if profile.groups and poor:
        out.append(_action("Limit outdoor time for children, older adults and anyone with asthma",
                           "These groups are affected at lower concentrations.",
                           "Reduces risk of symptoms and clinic visits."))
    if profile.commute in OPEN_AIR_COMMUTES and poor:
        out.append(_action("Wear a well-fitted N95 or FFP2 mask on your commute",
                           "Open-air travel gives direct exposure; cloth and surgical masks filter little PM2.5.",
                           "A sealed N95 can remove about 95% of fine particles."))
    if profile.commute == "car" and poor:
        out.append(_action("Use recirculation mode and keep windows shut in traffic",
                           "Cabin air near vehicles carries concentrated exhaust.",
                           "Lowers in-car particle levels."))
    return out


def _indoor(profile: Profile, aqi: int) -> list[dict[str, str]]:
    poor = aqi > POOR_ABOVE
    out = []
    if poor:
        out += [
            _action("Ventilate briefly when air is cleanest, then close up",
                    "Constant open windows let smog in; none at all lets indoor pollutants build.",
                    "Balances fresh air with lower particle intake."),
            _action("Run a HEPA purifier in the room where you sleep",
                    "You spend about eight hours there each night.",
                    "Can cut indoor PM2.5 by 50% or more in a closed room."),
            _action("Wet-mop or use a damp cloth instead of dry sweeping",
                    "Dry sweeping lifts settled dust back into the air.",
                    "Keeps particles out of your breathing zone."),
        ]
        if profile.home == "apartment":
            out.append(_action("Seal gaps around doors and windows",
                               "Leaky frames let outdoor smog infiltrate.",
                               "Slows particle entry noticeably."))
    else:
        out.append(_action("Open windows to flush indoor air",
                           "Outdoor air is cleaner than most indoor air today.",
                           "Clears cooking and cleaning pollutants."))
    if profile.heating in COMBUSTION_HEATING:
        out.append(_action("Ventilate when heating and never burn fuel in a closed room",
                           "Combustion adds particles and carbon monoxide indoors.",
                           "Reduces a serious indoor hazard."))
    return out


def _alternatives(profile: Profile) -> list[dict[str, str]]:
    out = []
    if profile.heating == "wood_coal":
        out.append(_action("Switch to an electric heater or cleaner fuel when possible",
                           "Household burning is a major winter smog source.",
                           "Removes a large local emission source for your home and neighbours."))
    if profile.commute in {"car", "two_wheeler"}:
        out.append(_action("Carpool or take public transport two days a week",
                           "Fewer vehicles means less tailpipe and road-dust pollution.",
                           "A shared car trip roughly halves per-person emissions."))
    out += [
        _action("Never burn waste, leaves or plastic",
                "Open burning releases toxic particles at street level.",
                "Prevents a direct, hyper-local pollution spike."),
        _action("Cook with induction or electric and use the exhaust fan",
                "Cooking is a leading source of indoor particles.",
                "Lowers indoor PM2.5 during meals."),
    ]
    return out


def _summary(label: str, aqi: int, vulnerable: bool) -> str:
    base = f"AQI {aqi} is {label.lower()}."
    if aqi <= GOOD_MAX:
        return base + " Air is clean enough for all normal activity."
    if aqi <= POOR_ABOVE:
        return base + " Unusually sensitive people should watch for symptoms."
    note = " Your household includes people at higher risk." if vulnerable else ""
    return base + " Reduce exposure with the steps below." + note


def build_advice(profile: Profile, aqi: int) -> dict:
    """Build the full advice payload for a profile at a given AQI."""
    key, label = categorize(aqi)
    return {
        "aqi": aqi,
        "category": key,
        "label": label,
        "gauge_position": gauge_position(aqi),
        "summary": _summary(label, aqi, bool(profile.groups)),
        "routines": _routines(profile, aqi),
        "indoor": _indoor(profile, aqi),
        "alternatives": _alternatives(profile),
    }
