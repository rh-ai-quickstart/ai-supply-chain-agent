"""Tests for scenario ID resolution helpers."""

from services.simulation_intent import (
    format_impact_snapshot,
    normalize_scenario_id,
    resolve_scenario_id,
    scenario_context_block,
)


def test_resolve_scenario_id_prefers_explicit():
    assert (
        resolve_scenario_id("simulate the suez blockage", preferred="opensky-uk-closure-001")
        == "opensky-uk-closure-001"
    )


def test_resolve_scenario_id_from_clues():
    assert resolve_scenario_id("simulate the UK NATS GPS failure") == "opensky-uk-closure-001"
    assert resolve_scenario_id("port strike in LA") == "supply-chain-port-strike-la"
    assert resolve_scenario_id("suez canal block") == "supply-chain-suez-blockage"
    assert resolve_scenario_id("generic question") == ""


def test_normalize_prefers_active_scenario():
    assert (
        normalize_scenario_id(
            "UK NATS GPS failure",
            active_scenario_id="opensky-uk-closure-001",
            question="Which flights are affected?",
        )
        == "opensky-uk-closure-001"
    )


def test_normalize_accepts_known_model_id():
    assert (
        normalize_scenario_id(
            "opensky-uk-closure-001",
            active_scenario_id="",
            question="impact?",
        )
        == "opensky-uk-closure-001"
    )


def test_normalize_maps_free_text_when_no_active():
    assert (
        normalize_scenario_id(
            "UK NATS GPS failure",
            active_scenario_id="",
            question="Which flights are affected?",
        )
        == "opensky-uk-closure-001"
    )


def test_scenario_context_block_includes_description():
    block = scenario_context_block("opensky-uk-closure-001")
    assert "Active simulation scenario: opensky-uk-closure-001 (UK Airspace Closure)." in block
    assert "NATS GPS failure" in block
    assert "No Impact Query snapshot is loaded yet" in block
    assert "Do not redirect" not in block


def test_scenario_context_block_infers_from_user_text():
    block = scenario_context_block("", user_text="Tell me about the suez canal block")
    assert "supply-chain-suez-blockage" in block
    assert "Suez Canal is blocked" in block


def test_scenario_context_block_includes_impact_snapshot():
    block = scenario_context_block(
        "opensky-uk-closure-001",
        impact={
            "scenario_id": "opensky-uk-closure-001",
            "answer": "Two flights diverted.",
            "affected_entities": ["a", "b"],
            "solver": {
                "impact_score": 0.2,
                "total_value_at_risk": 50,
                "currency": "USD",
                "value_breakdown": [
                    {"entity_id": "b", "value_usd": 10},
                    {"entity_id": "a", "value_usd": 40},
                ],
            },
        },
    )
    assert "Latest Impact Query result" in block
    assert "Two flights diverted." in block
    assert "a, b" in block
    assert "Do not redirect the user to Impact Query" in block
    assert "No Impact Query snapshot is loaded yet" not in block
    # Highest value first.
    assert block.index("a [flight]") < block.index("b [flight]")


def test_format_impact_snapshot_truncates_long_entity_lists():
    entities = [f"e{i}" for i in range(20)]
    text = format_impact_snapshot({"affected_entities": entities, "answer": "ok"})
    assert "(+8 more)" in text
    assert "e0" in text
    assert "e19" not in text


def test_format_impact_snapshot_ranks_and_caps_value_breakdown():
    breakdown = [{"entity_id": f"flight-{i}", "value_usd": float(i)} for i in range(20)]
    breakdown.append({"entity_id": "cargo-flight-19-1", "value_usd": 100.5, "callsign": "BAW442"})
    text = format_impact_snapshot(
        {
            "answer": "ok",
            "solver": {
                "currency": "USD",
                "total_value_at_risk": 999,
                "value_breakdown": breakdown,
            },
        }
    )
    assert "value_breakdown (top 15 by value_usd" in text
    assert "cargo-flight-19-1 [cargo] (callsign=BAW442): 100.5 USD" in text
    assert "flight-19 [flight]: 19 USD" in text
    assert "flight-0 [flight]" not in text
    assert text.index("cargo-flight-19-1") < text.index("flight-19")


def test_format_impact_snapshot_skips_invalid_breakdown_rows():
    text = format_impact_snapshot(
        {
            "solver": {
                "value_breakdown": [
                    {"entity_id": "ok", "value_usd": 5},
                    {"entity_id": "", "value_usd": 99},
                    {"entity_id": "zero", "value_usd": 0},
                    {"entity_id": "bad", "value_usd": "n/a"},
                    "not-a-dict",
                ],
            }
        }
    )
    assert "ok [flight]: 5 USD" in text
    assert "zero" not in text
    assert "bad" not in text
