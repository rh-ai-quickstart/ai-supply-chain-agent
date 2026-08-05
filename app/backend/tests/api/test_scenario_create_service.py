"""Tests for scenario propose/create helpers and service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.scenario_create_service import (
    ScenarioCreateService,
    normalize_draft,
    parse_propose_json,
    validate_bbox,
)


def test_validate_bbox_ok():
    assert validate_bbox("-5.0,42.0,8.5,51.5") == "-5.0,42.0,8.5,51.5"


def test_validate_bbox_rejects_inverted():
    with pytest.raises(ValueError, match="minLon < maxLon"):
        validate_bbox("10,40,5,50")


def test_validate_bbox_rejects_bad_shape():
    with pytest.raises(ValueError, match="affect_bbox"):
        validate_bbox("not-a-bbox")


def test_parse_propose_json_plain():
    raw = (
        '{"name":"France Airspace Closure","scenario_id":"france-airspace-closure",'
        '"description":"French FIR closed.","affect_bbox":"-5,42,8,51",'
        '"place_summary":"France","rationale":"Covers metropolitan France."}'
    )
    draft = parse_propose_json(raw)
    assert draft["scenario_id"] == "france-airspace-closure"
    assert draft["affect_bbox"] == "-5.0,42.0,8.0,51.0"
    assert draft["name"] == "France Airspace Closure"


def test_parse_propose_json_fenced_and_slugifies_missing_id():
    raw = """```json
{"name": "Port Strike Marseille", "description": "Strike at Fos.",
 "affect_bbox": "4.8,43.2,5.5,43.5", "place_summary": "Marseille", "rationale": "Port area"}
```"""
    draft = parse_propose_json(raw)
    assert draft["scenario_id"] == "port-strike-marseille"
    assert "Fos" in draft["description"]


def test_normalize_draft_rejects_bad_scenario_id():
    with pytest.raises(ValueError, match="scenario_id"):
        normalize_draft(
            {
                "name": "X",
                "scenario_id": "Bad_ID",
                "description": "d",
                "affect_bbox": "0,0,1,1",
            }
        )


def test_propose_success():
    llm = MagicMock()
    completion = MagicMock()
    completion.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    '{"name":"France Closure","scenario_id":"france-closure",'
                    '"description":"Closed.","affect_bbox":"-5,42,8,51",'
                    '"place_summary":"France","rationale":"FIR"}'
                )
            )
        )
    ]
    completion.model_dump.return_value = {"id": "c1"}
    llm._client.chat.completions.create.return_value = completion
    llm._completion_kwargs.side_effect = lambda messages, stream=False, **kw: {
        "model": "m",
        "messages": messages,
    }
    llm._completion_to_json.return_value = {"id": "c1"}

    service = ScenarioCreateService(llama_stack_client=llm, general_simulation_client=MagicMock())
    out = service.propose("Close French airspace")
    assert out["success"] is True
    assert out["draft"]["scenario_id"] == "france-closure"
    llm._client.chat.completions.create.assert_called_once()


def test_propose_empty_prompt():
    service = ScenarioCreateService(llama_stack_client=MagicMock(), general_simulation_client=MagicMock())
    assert service.propose("  ") == {"success": False, "error": "prompt is required"}


def test_create_success():
    gen = MagicMock()
    gen.create_event.return_value = {
        "status": "injected",
        "event_id": "evt-france-closure",
        "affected_count": 3,
        "affect_bbox": "-5.0,42.0,8.0,51.0",
    }
    gen.sync_spatial.return_value = {"status": "ok"}
    service = ScenarioCreateService(llama_stack_client=MagicMock(), general_simulation_client=gen)
    out = service.create(
        {
            "name": "France Closure",
            "scenario_id": "france-closure",
            "description": "Closed.",
            "affect_bbox": "-5,42,8,51",
            "place_summary": "France",
            "rationale": "FIR",
        }
    )
    assert out["success"] is True
    assert out["scenario_id"] == "france-closure"
    assert out["affected_count"] == 3
    gen.create_event.assert_called_once()
    kwargs = gen.create_event.call_args.kwargs
    assert kwargs["scenario_id"] == "france-closure"
    assert kwargs["bbox"] == "-5.0,42.0,8.0,51.0"
    gen.sync_spatial.assert_called_once_with("france-closure")


def test_create_propagates_gen_sim_error():
    gen = MagicMock()
    gen.create_event.return_value = {"error": "HTTP 400: bad bbox"}
    service = ScenarioCreateService(llama_stack_client=MagicMock(), general_simulation_client=gen)
    out = service.create(
        {
            "name": "X",
            "scenario_id": "x",
            "description": "d",
            "affect_bbox": "0,0,1,1",
        }
    )
    assert out["success"] is False
    assert "HTTP 400" in out["error"]
