import logging
import random

from clients.opensky_client import OpenSkyClient
from services.supply_chain_state_builder import (
    SupplyChainStateBuilder,
    get_static_fallback_data,
)

logger = logging.getLogger(__name__)


class DashboardService:
    """Dashboard payloads aligned with legacy `app/__legacy/app.py` (OpenSky + map data)."""

    def __init__(self, state_builder: SupplyChainStateBuilder | None = None) -> None:
        self._builder = state_builder or SupplyChainStateBuilder(OpenSkyClient())

    def get_state(self):
        return self._builder.build_state()

    def trigger_event(self, map_view: str):
        return self._builder.trigger_event(map_view)

    def simulate(self, scenario: str, optimize: bool):
        try:
            result = self._builder.build_state()
        except Exception as exc:
            logger.warning("simulate: falling back to static data (%s)", exc)
            result = get_static_fallback_data()

        if scenario == "port-strike":
            result["kpis"]["lostSales"] = {
                "value": "$4.2M",
                "trendSymbol": "▲",
                "trendClass": "down",
            }
            if "global" in result.get("alerts", {}):
                result["alerts"]["global"].insert(
                    0,
                    {
                        "type": "critical",
                        "text": "SIMULATION: Port Strike impact high. Rerouting recommended.",
                    },
                )
            if "revenue" in result.get("charts", {}):
                result["charts"]["revenue"]["revenueData"] = [60, 50, 40, 80, 70]
                result["charts"]["revenue"]["colors"] = ["red", "red", "red", "red", "red"]

        elif scenario == "geopolitical":
            result["kpis"]["turnover"] = {
                "value": "3.1x",
                "trendSymbol": "▼",
                "trendClass": "down",
            }
            if "global" in result.get("alerts", {}):
                result["alerts"]["global"].insert(
                    0,
                    {
                        "type": "critical",
                        "text": "SIMULATION: Suez blockage. 14-day delay projected.",
                    },
                )

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
