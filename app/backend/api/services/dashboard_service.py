import json
import logging
import random
from pathlib import Path

from clients.opensky_client import OpenSkyClient
from services.supply_chain_state_builder import (
    SupplyChainStateBuilder,
    get_static_fallback_data,
)

logger = logging.getLogger(__name__)

_SCENARIOS_PATH = Path(__file__).resolve().parent.parent / "data" / "scenarios.json"

_scenarios_cache: dict | None = None


def _load_scenarios() -> dict:
    global _scenarios_cache
    if _scenarios_cache is None:
        with _SCENARIOS_PATH.open("r", encoding="utf-8") as handle:
            _scenarios_cache = json.load(handle)
    return _scenarios_cache


def _apply_mutation(payload: dict, mutation: dict) -> None:
    op = mutation["op"]
    path = mutation["path"]
    value = mutation["value"]

    parent = payload
    for key in path[:-1]:
        parent = parent.setdefault(key, {})

    if op == "set":
        parent[path[-1]] = value
    elif op == "prepend":
        container = parent.get(path[-1])
        if not isinstance(container, list):
            container = []
            parent[path[-1]] = container
        container.insert(0, value)
    else:
        raise ValueError(f"Unsupported scenario mutation op: {op}")


class DashboardService:
    """Dashboard payloads combining OpenSky flight data with map data."""

    def __init__(self, state_builder: SupplyChainStateBuilder | None = None) -> None:
        self._builder = state_builder or SupplyChainStateBuilder(OpenSkyClient())

    def get_state(self):
        return self._builder.build_state()

    def trigger_event(self, map_view: str):
        return self._builder.trigger_event(map_view)

    def simulate(self, scenario: str, optimize: bool):
        try:
            result = self._builder.build_state()
        # Broad catch: build_state may raise varied live-data errors; fall back to static data.
        except Exception as exc:
            logger.warning("simulate: falling back to static data (%s)", exc)
            result = get_static_fallback_data()

        scenario_config = _load_scenarios().get(scenario)
        if scenario_config:
            for mutation in scenario_config.get("mutations", []):
                _apply_mutation(result, mutation)

        if optimize:
            total_tokens = random.randint(3500, 4200)
            tps = random.randint(110, 140)
            result["performance"] = {
                "mode": "Distributed (vLLM)",
                "cacheRate": f"{random.randint(89, 96)}%",
                "latency": f"{random.uniform(0.3, 0.6):.2f}s",
                "costSavings": f"{random.randint(45, 60)}%",
                "totalTokens": f"{total_tokens}",
                "tokensPerSecond": f"{tps} t/s",
            }
        else:
            total_tokens = random.randint(3500, 4200)
            tps = random.randint(12, 25)
            result["performance"] = {
                "mode": "Standard Monolithic",
                "cacheRate": "0%",
                "latency": f"{random.uniform(2.8, 3.5):.2f}s",
                "costSavings": "0%",
                "totalTokens": f"{total_tokens}",
                "tokensPerSecond": f"{tps} t/s",
            }

        return result
