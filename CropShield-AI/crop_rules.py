from __future__ import annotations

from collections.abc import Mapping

SOIL_MOISTURE_VALUES = {"dry", "adequate", "wet", "unknown"}


def assess_field_risk(observations: Mapping[str, object]) -> dict:
    """Calculate a deterministic, explainable screening score from observations."""
    required_flags = ("wilting", "yellowing", "standing_water")
    for name in required_flags:
        if name not in observations or not isinstance(observations[name], bool):
            raise ValueError(f"{name} must be provided as a boolean.")

    moisture = observations.get("soil_moisture")
    if not isinstance(moisture, str) or moisture.casefold() not in SOIL_MOISTURE_VALUES:
        raise ValueError(
            "soil_moisture must be dry, adequate, wet, or unknown."
        )
    moisture = moisture.casefold()

    flags = []
    if observations["wilting"]:
        flags.append(
            {
                "risk": "Wilting observed",
                "severity": "Moderate",
                "score": 3,
                "reason": "Wilting can be associated with water stress or other crop stress.",
            }
        )
    if observations["yellowing"]:
        flags.append(
            {
                "risk": "Leaf yellowing observed",
                "severity": "Moderate",
                "score": 2,
                "reason": "Yellowing can have multiple causes and needs field context.",
            }
        )
    if observations["standing_water"]:
        flags.append(
            {
                "risk": "Standing water observed",
                "severity": "Elevated",
                "score": 3,
                "reason": "Persistent standing water may indicate drainage or root-zone stress.",
            }
        )
    if moisture == "dry":
        flags.append(
            {
                "risk": "Dry soil reported",
                "severity": "Moderate",
                "score": 2,
                "reason": "Dry soil may contribute to water stress; verify moisture near roots.",
            }
        )
    elif moisture == "wet":
        flags.append(
            {
                "risk": "Wet soil reported",
                "severity": "Moderate",
                "score": 2,
                "reason": "Wet soil may contribute to root-zone stress, especially if persistent.",
            }
        )

    score = min(10, sum(flag["score"] for flag in flags))
    level = "Low" if score <= 2 else "Moderate" if score <= 5 else "High"
    return {"score": score, "level": level, "flags": flags}


def create_action_plan(risk: Mapping[str, object]) -> list[str]:
    """Create cautious, non-chemical next steps based on the local rule results."""
    flags = risk.get("flags", [])
    if not isinstance(flags, list):
        raise ValueError("risk flags must be a list.")

    steps = [
        "Recheck a few affected and unaffected plants, and note whether symptoms are spreading.",
        "Record the date, field location, growth stage, and any recent management changes.",
    ]
    if any(
        isinstance(flag, dict) and flag.get("risk") in {
            "Dry soil reported",
            "Wilting observed",
        }
        for flag in flags
    ):
        steps.append(
            "Check soil moisture near the active root zone before making irrigation changes."
        )
    if any(
        isinstance(flag, dict) and flag.get("risk") in {
            "Standing water observed",
            "Wet soil reported",
        }
        for flag in flags
    ):
        steps.append(
            "Check whether water is persisting and inspect field drainage without disturbing plants unnecessarily."
        )
    if any(
        isinstance(flag, dict) and flag.get("risk") == "Leaf yellowing observed"
        for flag in flags
    ):
        steps.append(
            "Note which leaves are affected first and whether the pattern is uniform or patchy."
        )
    steps.append(
        "If symptoms worsen or the cause is uncertain, contact a qualified agricultural officer or local extension service."
    )
    return steps
