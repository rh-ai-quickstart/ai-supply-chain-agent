"""Builds dashboard payloads for the supply chain dashboard."""

from __future__ import annotations

import copy
import json
import logging
import os
import random
import threading
import time
from pathlib import Path
from typing import Any

from clients.opensky_client import OpenSkyClient
from services.flight_tracking_service import FlightTrackingService

logger = logging.getLogger(__name__)

EVENT_DURATION_SECONDS = 120

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "config.json"
_CONFIG_ENV_VAR = "SUPPLY_CHAIN_CONFIG_PATH"

_config_cache: dict[str, Any] | None = None


def _load_config() -> dict[str, Any]:
    """Load the supply-chain data config, cached after first read.

    The config path can be overridden via the ``SUPPLY_CHAIN_CONFIG_PATH``
    environment variable (useful for tooling/tests).
    """
    global _config_cache
    if _config_cache is None:
        path = Path(os.environ.get(_CONFIG_ENV_VAR, _DEFAULT_CONFIG_PATH))
        with path.open("r", encoding="utf-8") as handle:
            _config_cache = json.load(handle)
    return _config_cache


_event_lock = threading.Lock()
_event_slot: dict[str, Any] = {"event": None, "timestamp": 0.0}


def _get_simulated_world_event(
    map_view: str = "global", force_new: bool = False
) -> dict[str, Any] | None:
    """Match legacy `get_simulated_world_event` TTL and map-view branching."""
    current_time = time.time()
    with _event_lock:
        active = _event_slot.get("event")
        if active is not None and not force_new:
            if (current_time - float(_event_slot["timestamp"])) > EVENT_DURATION_SECONDS:
                _event_slot["event"] = None
                _event_slot["timestamp"] = 0.0
                return None
            return active

        if not force_new:
            return None

        if map_view == "regional":
            new_event = {
                "type": "warning",
                "text": "LABOR DISPUTE: LA/LGB negotiations stalled. AI recommends diversion.",
                "action": {"id": "propose_diversion_la", "text": "AI: View Options"},
            }
        elif map_view == "airFreight":
            new_event = {
                "type": "critical",
                "text": "LIVE THREAT: Alaskan Storm. Airspace closing. AI recommends rerouting.",
                "action": {"id": "mcp-reroute-1", "text": "AI: View Reroute"},
            }
        else:
            new_event = {
                "type": "critical",
                "text": "NEW THREAT: Cyclone 'Atlas' threatens Singapore. AI recommends rerouting.",
                "action": {"id": "propose_reroute_sin", "text": "AI: View Options"},
            }

        _event_slot["event"] = new_event
        _event_slot["timestamp"] = current_time
        return new_event


class _AirFreightAggregator:
    """Ports, routes, and live or fallback air assets (legacy MCPAgent)."""

    def __init__(self, opensky: OpenSkyClient) -> None:
        config = _load_config()
        self.airports = list(config["airports"])
        self.air_routes = list(config["airRoutes"])
        self._cargo_watchlist = list(config["cargoWatchlist"])
        self._fallback_hubs = list(config["fallbackPlaneHubs"])
        self._flight_tracking = FlightTrackingService(opensky, self._cargo_watchlist)

    def _generate_fallback_planes(self) -> list[dict[str, Any]]:
        planes: list[dict[str, Any]] = []
        hubs = self._fallback_hubs
        for i in range(30):
            hub = random.choice(hubs)
            prefix = random.choice(self._cargo_watchlist)
            planes.append(
                {
                    "id": f"sim-cargo-{i}",
                    "name": f"{prefix}{random.randint(100, 9999)} (Sim)",
                    "cargo": "Mixed Freight",
                    "routeId": None,
                    "is_live": True,
                    "lat": hub[0] + random.uniform(-15, 15),
                    "lng": hub[1] + random.uniform(-15, 15),
                    "track": random.randint(0, 360),
                    "speed": f"{random.randint(450, 600)} mph",
                    "altitude_ft": f"{random.randint(30000, 42000)} ft",
                }
            )
        for i in range(70):
            hub = random.choice(hubs)
            planes.append(
                {
                    "id": f"sim-gen-{i}",
                    "name": f"FLT{random.randint(100, 9999)} (Gen)",
                    "cargo": "General Cargo",
                    "routeId": None,
                    "is_live": True,
                    "lat": hub[0] + random.uniform(-20, 20),
                    "lng": hub[1] + random.uniform(-20, 20),
                    "track": random.randint(0, 360),
                    "speed": f"{random.randint(400, 550)} mph",
                    "altitude_ft": f"{random.randint(25000, 38000)} ft",
                }
            )
        return planes

    def get_live_air_state(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        alerts: list[dict[str, Any]] = []
        live_planes = self._flight_tracking.get_live_planes()

        if not live_planes:
            alerts.append(
                {
                    "type": "warning",
                    "text": "OpenSky connection slow. Displaying predicted flight paths.",
                }
            )
            live_planes = self._generate_fallback_planes()

        logger.info("Air freight display count: %s", len(live_planes))

        return {
            "ports": list(self.airports),
            "routes": list(self.air_routes),
            "assets": live_planes,
            "riskZones": [],
        }, alerts


def get_static_fallback_data() -> dict[str, Any]:
    return copy.deepcopy(_load_config()["staticFallback"])


class SupplyChainStateBuilder:
    """Assembles KPIs, alerts, charts, and map layers like the legacy Flask app."""

    def __init__(self, opensky_client: OpenSkyClient | None = None) -> None:
        self._opensky = opensky_client or OpenSkyClient()
        self._air = _AirFreightAggregator(self._opensky)

    def _sea_freight_data(self) -> dict[str, Any]:
        return copy.deepcopy(_load_config()["seaFreight"])

    def _land_freight_data(self) -> dict[str, Any]:
        return copy.deepcopy(_load_config()["landFreight"])

    def build_state(self) -> dict[str, Any]:
        air_freight_data, air_alerts = self._air.get_live_air_state()
        sea_freight_data = self._sea_freight_data()
        land_freight_data = self._land_freight_data()

        kpis = {
            "inStock": {"value": f"{random.randint(92, 98)}%"},
            "onTime": {"value": f"{random.randint(90, 96)}%"},
            "turnover": {"value": f"{random.uniform(4.5, 5.5):.1f}x"},
            "lostSales": {"value": f"${random.uniform(0.1, 0.3):.1f}M"},
            "reorderPoint": {"value": f"{random.randint(18, 22)}%"},
        }

        new_event = _get_simulated_world_event()
        global_alerts = [{"type": "info", "text": "System nominal. All sea routes clear."}]

        if new_event:
            if new_event["action"]["id"] == "mcp-reroute-1":
                air_alerts.insert(0, new_event)
                air_freight_data["riskZones"].append(
                    {
                        "id": "risk-storm-1",
                        "name": "Alaskan Storm System",
                        "lat": 55,
                        "lng": -160,
                        "severity": 0.8,
                    }
                )
                air_freight_data["routes"].append(
                    {
                        "id": "HKG-LAX-REROUTE",
                        "start": [113.91, 22.30],
                        "end": [-118.40, 33.94],
                        "color": "yellow",
                    }
                )
                air_freight_data["assets"].append(
                    {
                        "id": "SIM-REROUTE",
                        "name": "Simulated Reroute",
                        "cargo": "Priority Goods",
                        "routeId": "HKG-LAX-REROUTE",
                        "is_live": False,
                        "progress": 0.6,
                        "speed": 550,
                        "capacity": 90,
                        "track": 100,
                    }
                )
            else:
                global_alerts.insert(0, new_event)

        alerts = {
            "global": global_alerts,
            "regional": [{"type": "warning", "text": "Chicago DC approaching 85% capacity."}],
            "airFreight": air_alerts,
        }

        rev_data = [random.randint(85, 115) for _ in range(5)]
        charts = {
            "demand": {
                "labels": ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10", "W11", "W12"],
                "actual": [random.randint(40, 60) for _ in range(12)],
                "forecast": [random.randint(40, 60) for _ in range(12)],
                "annotation": None,
            },
            "revenue": {
                "revenueData": rev_data,
                "marginData": [random.randint(20, 45) for _ in range(5)],
                "colors": ["green" if x >= 100 else "red" for x in rev_data],
            },
        }

        map_data = {
            "global": sea_freight_data,
            "regional": land_freight_data,
            "airFreight": air_freight_data,
        }

        return {
            "kpis": kpis,
            "alerts": alerts,
            "charts": charts,
            "mapData": map_data,
        }

    def trigger_event(self, map_view: str) -> dict[str, Any]:
        _get_simulated_world_event(map_view=map_view, force_new=True)
        return self.build_state()
