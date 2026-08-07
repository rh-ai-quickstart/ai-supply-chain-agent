"""Tests for scenario ID resolution helpers."""

from services.simulation_intent import normalize_scenario_id, resolve_scenario_id


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
