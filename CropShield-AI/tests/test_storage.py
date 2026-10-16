import csv
import json

import pytest

from storage import get_sample_reports, load_reports, save_report


def make_report(crop="Wheat"):
    return {
        "created_at": "2026-02-03T10:30:00+00:00",
        "crop": crop,
        "growth_stage": "Vegetative",
        "symptoms": "A few leaves are yellow.",
        "affected_area": "North field",
        "observations": {"yellowing": True, "soil_moisture": "adequate"},
        "risk_score": 2,
        "risk_level": "Low",
        "risk_flags": [{"risk": "Leaf yellowing observed", "score": 2}],
        "action_plan": ["Observe and record changes."],
        "ai_explanation": "",
        "follow_up_questions": [],
        "ai_status": "Not requested",
        "synthetic": False,
    }


def test_missing_report_file_loads_as_empty(tmp_path):
    assert load_reports(tmp_path / "missing.csv") == []


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "reports.csv"
    first = make_report()
    second = make_report("Corn")

    save_report(first, path)
    save_report(second, path)

    loaded = load_reports(path)
    assert len(loaded) == 2
    assert loaded[0]["crop"] == "Wheat"
    assert loaded[0]["observations"] == first["observations"]
    assert loaded[0]["risk_flags"] == first["risk_flags"]
    assert loaded[1]["crop"] == "Corn"
    assert loaded[1]["synthetic"] is False


def test_invalid_json_in_report_is_reported(tmp_path):
    path = tmp_path / "reports.csv"
    save_report(make_report(), path)
    with path.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    rows[0]["observations"] = "{not-json"
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="Invalid report data"):
        load_reports(path)


def test_report_requires_core_fields():
    with pytest.raises(ValueError, match="missing required fields"):
        save_report({"crop": "Wheat"}, "unused.csv")


def test_demo_samples_are_explicitly_synthetic_and_not_persisted(tmp_path):
    samples = get_sample_reports()

    assert samples
    assert all(report["synthetic"] for report in samples)
    assert all("fictional" in report["crop"].casefold() for report in samples)
    assert load_reports(tmp_path / "reports.csv") == []
    assert all(
        sum(flag["score"] for flag in report["risk_flags"]) == report["risk_score"]
        for report in samples
    )
