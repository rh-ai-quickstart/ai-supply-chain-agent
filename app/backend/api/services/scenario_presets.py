"""Scenario default questions — mirrors frontend presetScenarioIds.js."""

SCENARIO_QUESTIONS: dict[str, str] = {
    "opensky-uk-closure-001": (
        "UK airspace is closed due to a NATS GPS failure. Which aircraft are affected, "
        "what diversions should be issued, and what is the estimated cost of impact?"
    ),
    "supply-chain-port-strike-la": (
        "Port of Los Angeles and Long Beach are closed by a strike. Which vessels, cargo, "
        "and inland facilities are affected, and what is the estimated cost of impact?"
    ),
    "supply-chain-suez-blockage": (
        "The Suez Canal is blocked. Which vessels and cargoes are delayed, what is the "
        "impact on European ports, and what is the estimated cost of impact?"
    ),
}

DEFAULT_IMPACT_QUESTION = SCENARIO_QUESTIONS["opensky-uk-closure-001"]


def question_for_scenario(scenario_id: str) -> str:
    return SCENARIO_QUESTIONS.get(scenario_id, DEFAULT_IMPACT_QUESTION)
