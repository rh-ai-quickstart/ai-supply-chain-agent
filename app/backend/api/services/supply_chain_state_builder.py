"""Builds dashboard payloads matching legacy `app/__legacy/app.py` behavior."""

from __future__ import annotations

import logging
import random
import threading
import time
from typing import Any

from clients.opensky_client import OpenSkyClient

logger = logging.getLogger(__name__)

CARGO_WATCHLIST = [
    "FDX",
    "UPS",
    "GTI",
    "KAL",
    "CKS",
    "AMZ",
    "DHL",
    "PAC",
    "GEC",
    "ATLAS",
    "CLX",
    "BOX",
    "RPA",
    "N8",
    "ABW",
    "CJT",
    "DAL",
    "UAL",
    "AAL",
    "BAW",
    "DLH",
    "AFR",
    "CPA",
    "ANA",
    "JAL",
    "QFA",
    "UAE",
    "ETH",
    "QTR",
    "SAS",
    "KLM",
    "SIA",
    "CSN",
    "CES",
]

EVENT_DURATION_SECONDS = 120

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
        self._opensky = opensky
        self.airports = [
            {
                "id": "ANC",
                "name": "Anchorage (ANC)",
                "lat": 61.17,
                "lng": -149.99,
                "inventory": 200,
                "risk": 10,
                "buffer": 50,
            },
            {
                "id": "LAX",
                "name": "Los Angeles (LAX)",
                "lat": 33.94,
                "lng": -118.40,
                "inventory": 150,
                "risk": 20,
                "buffer": 40,
            },
            {
                "id": "JFK",
                "name": "New York (JFK)",
                "lat": 40.64,
                "lng": -73.77,
                "inventory": 180,
                "risk": 15,
                "buffer": 45,
            },
            {
                "id": "FRA",
                "name": "Frankfurt (FRA)",
                "lat": 50.03,
                "lng": 8.57,
                "inventory": 220,
                "risk": 10,
                "buffer": 60,
            },
            {
                "id": "HKG",
                "name": "Hong Kong (HKG)",
                "lat": 22.30,
                "lng": 113.91,
                "inventory": 300,
                "risk": 5,
                "buffer": 70,
            },
        ]
        self.air_routes = [
            {"id": "HKG-ANC", "start": [113.91, 22.30], "end": [-149.99, 61.17], "primary": True},
            {"id": "FRA-JFK", "start": [8.57, 50.03], "end": [-73.77, 40.64], "primary": True},
            {"id": "ANC-LAX", "start": [-149.99, 61.17], "end": [-118.40, 33.94], "primary": True},
        ]

    def _generate_fallback_planes(self) -> list[dict[str, Any]]:
        planes: list[dict[str, Any]] = []
        hubs = [
            (35.0, -90.0),
            (38.0, -85.0),
            (61.0, -149.0),
            (22.0, 114.0),
            (50.0, 8.0),
            (25.0, 55.0),
            (1.0, 103.0),
            (34.0, -118.0),
            (40.0, -74.0),
            (51.0, 0.0),
            (35.0, 139.0),
        ]
        for i in range(30):
            hub = random.choice(hubs)
            prefix = random.choice(CARGO_WATCHLIST)
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
        live_states = self._opensky.fetch_states()
        live_planes: list[dict[str, Any]] = []
        alerts: list[dict[str, Any]] = []

        if live_states:
            for state in live_states:
                try:
                    if state[8]:
                        continue
                    callsign = state[1].strip() if state[1] else ""
                    if any(callsign.startswith(prefix) for prefix in CARGO_WATCHLIST):
                        velocity = state[9] if state[9] is not None else 0
                        altitude = state[7] if state[7] is not None else 0
                        live_planes.append(
                            {
                                "id": state[0],
                                "name": f"{callsign} (Live)",
                                "cargo": "Mixed Freight",
                                "routeId": None,
                                "is_live": True,
                                "lat": state[6],
                                "lng": state[5],
                                "track": state[10],
                                "speed": f"{velocity * 2.237:.0f} mph",
                                "altitude_ft": f"{altitude * 3.28084:.0f} ft",
                            }
                        )
                except Exception:
                    continue

            target_density = 100
            if len(live_planes) < target_density:
                for state in live_states:
                    if len(live_planes) >= target_density:
                        break
                    try:
                        if state[8]:
                            continue
                        if any(p["id"] == state[0] for p in live_planes):
                            continue
                        if state[9] and state[9] > 100:
                            callsign = state[1].strip() if state[1] else "FLIGHT"
                            altitude = state[7] if state[7] is not None else 0
                            live_planes.append(
                                {
                                    "id": state[0],
                                    "name": f"{callsign} (General)",
                                    "cargo": "General Cargo",
                                    "routeId": None,
                                    "is_live": True,
                                    "lat": state[6],
                                    "lng": state[5],
                                    "track": state[10],
                                    "speed": f"{state[9] * 2.237:.0f} mph",
                                    "altitude_ft": f"{altitude * 3.28084:.0f} ft",
                                }
                            )
                    except Exception:
                        continue

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
    return {
        "kpis": {
            "inStock": {"value": "95%", "trendSymbol": "▲", "trendClass": "up"},
            "onTime": {"value": "92%", "trendSymbol": "▲", "trendClass": "up"},
            "turnover": {"value": "5.2x", "trendSymbol": "▲", "trendClass": "up"},
            "lostSales": {"value": "$0.2M", "trendSymbol": "▼", "trendClass": "down"},
            "reorderPoint": {"value": "20%", "trendSymbol": "▲", "trendClass": "up"},
        },
        "alerts": {
            "global": [
                {"type": "info", "text": "System running in SAFE MODE (Live data unavailable)."}
            ],
            "regional": [],
            "airFreight": [],
        },
        "charts": {
            "demand": {"labels": ["W1", "W2", "W3"], "actual": [50, 52, 55], "forecast": [51, 53, 54]},
            "revenue": {
                "revenueData": [100, 100, 100, 100, 100],
                "marginData": [30, 30, 30, 30, 30],
                "colors": ["green"] * 5,
            },
        },
        "mapData": {
            "global": {"ports": [], "routes": [], "assets": [], "riskZones": []},
            "regional": {"ports": [], "routes": [], "assets": [], "riskZones": []},
            "airFreight": {"ports": [], "routes": [], "assets": [], "riskZones": []},
        },
    }


class SupplyChainStateBuilder:
    """Assembles KPIs, alerts, charts, and map layers like the legacy Flask app."""

    def __init__(self, opensky_client: OpenSkyClient | None = None) -> None:
        self._opensky = opensky_client or OpenSkyClient()
        self._air = _AirFreightAggregator(self._opensky)

    def _sea_freight_data(self) -> dict[str, Any]:
        return {
            "ports": [
                {"id": "sh", "name": "Shanghai", "lat": 31.23, "lng": 121.47, "risk": 15},
                {"id": "la", "name": "Los Angeles", "lat": 33.7, "lng": -118.29, "risk": 20},
                {"id": "rot", "name": "Rotterdam", "lat": 51.90, "lng": 4.48, "risk": 10},
                {"id": "sin", "name": "Singapore", "lat": 1.29, "lng": 103.85, "risk": 5},
                {"id": "nyk", "name": "Newark", "lat": 40.69, "lng": -74.17, "risk": 25},
            ],
            "routes": [
                {"id": "SH-LA", "start": [121.47, 31.23], "end": [-118.29, 33.7]},
                {"id": "RO-LA", "start": [4.48, 51.90], "end": [-118.29, 33.7]},
                {"id": "SG-LA", "start": [103.85, 1.29], "end": [-118.29, 33.7]},
                {"id": "SH-RO", "start": [121.47, 31.23], "end": [4.48, 51.90]},
                {"id": "RO-NK", "start": [4.48, 51.90], "end": [-74.17, 40.69]},
            ],
            "assets": [
                {
                    "name": "Vessel Alpha",
                    "cargo": "Electronics",
                    "routeId": "SH-LA",
                    "progress": 0.45,
                    "track": 90,
                    "capacity": "12000 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel Bravo",
                    "cargo": "Apparel",
                    "routeId": "RO-LA",
                    "progress": 0.75,
                    "track": 85,
                    "capacity": "8500 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel Charlie",
                    "cargo": "Raw Goods",
                    "routeId": "SG-LA",
                    "progress": 0.20,
                    "track": 260,
                    "capacity": "15000 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel Delta",
                    "cargo": "Machinery",
                    "routeId": "SH-RO",
                    "progress": 0.85,
                    "track": 275,
                    "capacity": "9000 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel Echo",
                    "cargo": "Pharma",
                    "routeId": "RO-NK",
                    "progress": 0.50,
                    "track": 310,
                    "capacity": "5000 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel Foxtrot",
                    "cargo": "Auto Parts",
                    "routeId": "SH-LA",
                    "progress": 0.80,
                    "track": 95,
                    "capacity": "11000 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel Golf",
                    "cargo": "Grain",
                    "routeId": "SH-RO",
                    "progress": 0.30,
                    "track": 45,
                    "capacity": "7000 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel Hotel",
                    "cargo": "Furniture",
                    "routeId": "RO-LA",
                    "progress": 0.10,
                    "track": 180,
                    "capacity": "6000 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel India",
                    "cargo": "Oil",
                    "routeId": "SG-LA",
                    "progress": 0.60,
                    "track": 270,
                    "capacity": "20000 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel Juliet",
                    "cargo": "Coal",
                    "routeId": "SH-LA",
                    "progress": 0.25,
                    "track": 90,
                    "capacity": "14000 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel Kilo",
                    "cargo": "Steel",
                    "routeId": "SH-RO",
                    "progress": 0.55,
                    "track": 275,
                    "capacity": "10000 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel Lima",
                    "cargo": "Chemicals",
                    "routeId": "RO-NK",
                    "progress": 0.90,
                    "track": 310,
                    "capacity": "5500 TEU",
                    "is_live": False,
                },
                {
                    "name": "Vessel Mike",
                    "cargo": "Vehicles",
                    "routeId": "RO-LA",
                    "progress": 0.40,
                    "track": 85,
                    "capacity": "9000 TEU",
                    "is_live": False,
                },
            ],
            "riskZones": [],
        }

    def _land_freight_data(self) -> dict[str, Any]:
        return {
            "ports": [
                {"id": "la_dc", "name": "Los Angeles DC", "lat": 34.05, "lng": -118.24, "risk": 10},
                {"id": "chi_dc", "name": "Chicago DC", "lat": 41.87, "lng": -87.62, "risk": 25},
                {"id": "ny_dc", "name": "Newark Hub", "lat": 40.69, "lng": -74.17, "risk": 5},
                {"id": "dal_dc", "name": "Dallas DC", "lat": 32.77, "lng": -96.79, "risk": 5},
            ],
            "routes": [
                {"id": "LA-CHI", "start": [-118.24, 34.05], "end": [-87.62, 41.87]},
                {"id": "NY-CHI", "start": [-74.17, 40.69], "end": [-87.62, 41.87]},
                {"id": "LA-DAL", "start": [-118.24, 34.05], "end": [-96.79, 32.77]},
            ],
            "assets": [
                {
                    "name": "Truck 405A",
                    "cargo": "Apparel",
                    "routeId": "LA-CHI",
                    "progress": 0.6,
                    "track": 70,
                    "is_live": False,
                },
                {
                    "name": "Truck 102B",
                    "cargo": "Electronics",
                    "routeId": "NY-CHI",
                    "progress": 0.3,
                    "track": 280,
                    "is_live": False,
                },
                {
                    "name": "Truck 202C",
                    "cargo": "Auto Parts",
                    "routeId": "LA-DAL",
                    "progress": 0.8,
                    "track": 110,
                    "is_live": False,
                },
            ],
            "riskZones": [],
        }

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
