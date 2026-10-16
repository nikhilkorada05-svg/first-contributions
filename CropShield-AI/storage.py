from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any

REPORTS_FILE = Path(__file__).resolve().parent / "data" / "reports.csv"
JSON_FIELDS = {
    "observations",
    "risk_flags",
    "action_plan",
    "follow_up_questions",
}
REPORT_FIELDS = [
    "created_at",
    "crop",
    "growth_stage",
    "symptoms",
    "affected_area",
    "observations",
    "risk_score",
    "risk_level",
    "risk_flags",
    "action_plan",
    "ai_explanation",
    "follow_up_questions",
    "ai_status",
    "synthetic",
]
REQUIRED_FIELDS = {
    "created_at",
    "crop",
    "growth_stage",
    "symptoms",
    "observations",
    "risk_score",
    "risk_level",
    "risk_flags",
    "action_plan",
}


def _serialize_report(report: dict[str, Any]) -> dict[str, str]:
    missing = REQUIRED_FIELDS.difference(report)
    if missing:
        raise ValueError(f"Report is missing required fields: {', '.join(sorted(missing))}")
    serialized: dict[str, str] = {}
    for field in REPORT_FIELDS:
        value = report.get(field, "")
        if field in JSON_FIELDS:
            serialized[field] = json.dumps(value, ensure_ascii=False)
        elif field == "synthetic":
            serialized[field] = "true" if bool(value) else "false"
        else:
            serialized[field] = str(value)
    return serialized


def save_report(
    report: dict[str, Any], path: str | Path = REPORTS_FILE
) -> None:
    """Append a report to a local CSV, replacing it atomically."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    serialized = _serialize_report(report)
    existing = load_reports(target)
    previous_rows = [_serialize_report(item) for item in existing]

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            writer = csv.DictWriter(temporary, fieldnames=REPORT_FIELDS)
            writer.writeheader()
            writer.writerows(previous_rows)
            writer.writerow(serialized)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, target)
    except OSError:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def load_reports(path: str | Path = REPORTS_FILE) -> list[dict[str, Any]]:
    """Load local reports; a missing file is an empty report collection."""
    source = Path(path)
    if not source.exists():
        return []
    reports: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8", newline="") as report_file:
        reader = csv.DictReader(report_file)
        if reader.fieldnames is None or not set(REPORT_FIELDS).issubset(
            reader.fieldnames
        ):
            raise ValueError(f"{source} does not have the expected CropShield report columns.")
        for line_number, row in enumerate(reader, start=2):
            try:
                report: dict[str, Any] = dict(row)
                for field in JSON_FIELDS:
                    report[field] = json.loads(row[field] or "null")
                report["risk_score"] = int(row["risk_score"])
                report["synthetic"] = row.get("synthetic", "").casefold() == "true"
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"Invalid report data on line {line_number} of {source}."
                ) from exc
            reports.append(report)
    return reports


def get_sample_reports() -> list[dict[str, Any]]:
    """Return clearly fictional reports for dashboard demonstration only."""
    return [
        {
            "created_at": "2026-01-12T09:00:00+00:00",
            "crop": "Tomato (fictional)",
            "growth_stage": "Flowering",
            "symptoms": "Fictional sample: mild leaf yellowing on several plants.",
            "affected_area": "Demonstration plot A",
            "observations": {
                "wilting": False,
                "yellowing": True,
                "standing_water": False,
                "soil_moisture": "adequate",
                "other_observations": "Synthetic data for demonstration only.",
            },
            "risk_score": 2,
            "risk_level": "Low",
            "risk_flags": [
                {
                    "risk": "Leaf yellowing observed",
                    "severity": "Moderate",
                    "score": 2,
                    "reason": "Fictional demonstration flag.",
                }
            ],
            "action_plan": ["Fictional demonstration only; not field advice."],
            "ai_explanation": "",
            "follow_up_questions": [],
            "ai_status": "Synthetic sample",
            "synthetic": True,
        },
        {
            "created_at": "2026-01-19T14:30:00+00:00",
            "crop": "Maize (fictional)",
            "growth_stage": "Vegetative",
            "symptoms": "Fictional sample: wilting and wet soil reported.",
            "affected_area": "Demonstration plot B",
            "observations": {
                "wilting": True,
                "yellowing": False,
                "standing_water": True,
                "soil_moisture": "wet",
                "other_observations": "Synthetic data for demonstration only.",
            },
            "risk_score": 8,
            "risk_level": "High",
            "risk_flags": [
                {
                    "risk": "Wilting observed",
                    "severity": "Moderate",
                    "score": 3,
                    "reason": "Fictional demonstration flag.",
                },
                {
                    "risk": "Standing water observed",
                    "severity": "Elevated",
                    "score": 3,
                    "reason": "Fictional demonstration flag.",
                },
                {
                    "risk": "Wet soil reported",
                    "severity": "Moderate",
                    "score": 2,
                    "reason": "Fictional demonstration flag.",
                },
            ],
            "action_plan": ["Fictional demonstration only; not field advice."],
            "ai_explanation": "",
            "follow_up_questions": [],
            "ai_status": "Synthetic sample",
            "synthetic": True,
        },
    ]
