import pytest

from crop_rules import assess_field_risk, create_action_plan


def test_no_selected_indicators_has_zero_low_risk():
    result = assess_field_risk(
        {
            "wilting": False,
            "yellowing": False,
            "standing_water": False,
            "soil_moisture": "unknown",
        }
    )

    assert result == {"score": 0, "level": "Low", "flags": []}


def test_flags_explain_score_and_cap_at_ten():
    result = assess_field_risk(
        {
            "wilting": True,
            "yellowing": True,
            "standing_water": True,
            "soil_moisture": "dry",
        }
    )

    assert result["score"] == 10
    assert result["level"] == "High"
    assert sum(flag["score"] for flag in result["flags"]) == 10
    assert all(flag["reason"] for flag in result["flags"])


def test_wet_soil_is_reported_as_its_own_flag():
    result = assess_field_risk(
        {
            "wilting": False,
            "yellowing": False,
            "standing_water": False,
            "soil_moisture": "WET",
        }
    )

    assert result["score"] == 2
    assert result["flags"][0]["risk"] == "Wet soil reported"


@pytest.mark.parametrize(
    "observations",
    [
        {"wilting": "yes", "yellowing": False, "standing_water": False, "soil_moisture": "dry"},
        {"wilting": False, "yellowing": False, "standing_water": False, "soil_moisture": "muddy"},
        {"yellowing": False, "standing_water": False, "soil_moisture": "dry"},
    ],
)
def test_invalid_observations_are_rejected(observations):
    with pytest.raises(ValueError):
        assess_field_risk(observations)


def test_action_plan_responds_to_flags_and_includes_expert_escalation():
    risk = assess_field_risk(
        {
            "wilting": True,
            "yellowing": True,
            "standing_water": False,
            "soil_moisture": "dry",
        }
    )

    steps = create_action_plan(risk)

    assert any("root zone" in step for step in steps)
    assert any("which leaves" in step for step in steps)
    assert any("qualified agricultural officer" in step for step in steps)
