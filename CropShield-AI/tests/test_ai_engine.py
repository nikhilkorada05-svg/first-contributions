from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from ai_engine import OllamaError, explain_crop_problem, list_models


def response_with(payload):
    return SimpleNamespace(
        raise_for_status=Mock(),
        json=Mock(return_value=payload),
    )


def test_list_models_returns_sorted_names(monkeypatch):
    monkeypatch.setattr(
        "ai_engine.requests.get",
        lambda *args, **kwargs: response_with(
            {"models": [{"name": "zeta"}, {"name": "Alpha"}, {"name": "zeta"}]}
        ),
    )

    assert list_models() == ["Alpha", "zeta"]


def test_list_models_reports_unexpected_payload(monkeypatch):
    monkeypatch.setattr(
        "ai_engine.requests.get",
        lambda *args, **kwargs: response_with({"unexpected": []}),
    )

    with pytest.raises(OllamaError, match="unexpected model-list"):
        list_models()


def test_list_models_converts_connection_error(monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr("ai_engine.requests.get", raise_connection_error)

    with pytest.raises(OllamaError, match="Cannot connect to Ollama"):
        list_models()


def test_explain_crop_problem_extracts_answer_and_questions(monkeypatch):
    monkeypatch.setattr(
        "ai_engine.requests.post",
        lambda *args, **kwargs: response_with(
            {"message": {"content": "Possible explanations\nCould soil be dry?"}}
        ),
    )

    result = explain_crop_problem(
        model="local-model",
        crop="Tomato",
        growth_stage="Flowering",
        symptoms="Yellow leaves",
        affected_area="North side",
        observations="No standing water",
        risk={"level": "Low", "score": 2},
    )

    assert result["explanation"].startswith("Possible explanations")
    assert result["follow_up_questions"] == ["Could soil be dry?"]


def test_explain_crop_problem_rejects_malformed_payload(monkeypatch):
    monkeypatch.setattr(
        "ai_engine.requests.post",
        lambda *args, **kwargs: response_with({"message": {"content": ""}}),
    )

    with pytest.raises(OllamaError, match="empty or malformed"):
        explain_crop_problem(
            model="local-model",
            crop="Tomato",
            growth_stage="Flowering",
            symptoms="Yellow leaves",
            affected_area="",
            observations="",
            risk={"level": "Low", "score": 0},
        )
