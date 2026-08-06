"""Tests for simulation intent detection used by chat tool routing."""

from services.simulation_intent import is_simulation_intent, resolve_scenario_id


def test_is_simulation_intent_matches_simulate():
    assert is_simulation_intent("Can you simulate the UK airspace closure?")
    assert is_simulation_intent("Run an impact analysis for this scenario")
    assert is_simulation_intent("What is the value at risk?")
    assert is_simulation_intent("Which aircraft are affected by the closure?")


def test_is_simulation_intent_rejects_generic_chat():
    assert not is_simulation_intent("What documents mention port risk?")
    assert not is_simulation_intent("Summarize supplier risk")


def test_resolve_scenario_id_prefers_explicit():
    assert (
        resolve_scenario_id("simulate the suez blockage", preferred="opensky-uk-closure-001")
        == "opensky-uk-closure-001"
    )


def test_resolve_scenario_id_from_text():
    assert resolve_scenario_id("simulate the UK NATS GPS failure") == "opensky-uk-closure-001"
    assert resolve_scenario_id("simulate the port strike in LA") == "supply-chain-port-strike-la"
    assert resolve_scenario_id("what-if the Suez Canal is blocked") == "supply-chain-suez-blockage"
    assert resolve_scenario_id("simulate something") == ""


def test_normalize_scenario_id_prefers_active_ui_scenario():
    from services.simulation_intent import normalize_scenario_id

    assert (
        normalize_scenario_id(
            "UK NATS GPS failure",
            active_scenario_id="opensky-uk-closure-001",
            question="Which flights are affected?",
        )
        == "opensky-uk-closure-001"
    )


def test_normalize_scenario_id_maps_invented_labels():
    from services.simulation_intent import normalize_scenario_id

    assert (
        normalize_scenario_id(
            "UK NATS GPS failure",
            active_scenario_id="",
            question="Which flights are affected?",
        )
        == "opensky-uk-closure-001"
    )
    assert (
        normalize_scenario_id(
            "port strike LA",
            active_scenario_id="",
            question="",
        )
        == "supply-chain-port-strike-la"
    )
