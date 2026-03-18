import random


class DashboardService:
    """Produces lightweight dashboard payloads for the frontend."""

    def _generate_air_freight_assets(self):
        hubs = [
            {"name": "Anchorage", "lat": 61.17, "lng": -149.99},
            {"name": "LAX", "lat": 33.94, "lng": -118.40},
            {"name": "Frankfurt", "lat": 50.03, "lng": 8.57},
            {"name": "Hong Kong", "lat": 22.30, "lng": 113.91},
            {"name": "Singapore", "lat": 1.29, "lng": 103.85},
            {"name": "JFK", "lat": 40.64, "lng": -73.77},
        ]
        prefixes = ["FDX", "UPS", "DHL", "GTI", "CKS", "PAC", "CLX", "QTR"]
        assets = []
        for index in range(55):
            hub = random.choice(hubs)
            assets.append(
                {
                    "id": f"air-{index}",
                    "name": f"{random.choice(prefixes)}{random.randint(100, 9999)}",
                    "cargo": "Mixed Freight" if index < 25 else "General Cargo",
                    "lat": round(hub["lat"] + random.uniform(-14.0, 14.0), 4),
                    "lng": round(hub["lng"] + random.uniform(-14.0, 14.0), 4),
                    "speed": f"{random.randint(430, 610)} mph",
                }
            )
        return assets

    def get_state(self):
        in_stock = random.randint(92, 98)
        on_time = random.randint(89, 97)
        turnover = round(random.uniform(4.4, 5.6), 1)
        lost_sales = round(random.uniform(0.1, 0.5), 1)
        reorder_point = random.randint(18, 26)

        return {
            "kpis": {
                "inStock": {"value": f"{in_stock}%"},
                "onTime": {"value": f"{on_time}%"},
                "turnover": {"value": f"{turnover}x"},
                "lostSales": {"value": f"${lost_sales}M"},
                "reorderPoint": {"value": f"{reorder_point}%"},
            },
            "alerts": {
                "global": [
                    {"type": "info", "text": "System nominal. All sea routes clear."}
                ],
                "regional": [
                    {"type": "warning", "text": "Chicago DC approaching 85% capacity."}
                ],
                "airFreight": [
                    {
                        "type": "critical",
                        "text": "Alaskan weather window narrowing for selected routes.",
                    }
                ],
            },
            "charts": {
                "demand": {
                    "labels": ["W1", "W2", "W3", "W4"],
                    "actual": [52, 49, 57, 54],
                    "forecast": [53, 50, 56, 55],
                },
                "revenue": {
                    "revenueData": [101, 98, 96, 103, 100],
                    "marginData": [33, 30, 29, 35, 31],
                    "colors": ["green", "red", "red", "green", "green"],
                },
            },
            "mapData": {
                "global": {
                    "ports": [
                        {"name": "Shanghai", "lat": 31.23, "lng": 121.47, "risk": 15},
                        {"name": "Los Angeles", "lat": 33.7, "lng": -118.29, "risk": 20},
                        {"name": "Rotterdam", "lat": 51.9, "lng": 4.48, "risk": 10},
                    ],
                    "assets": [
                        {"id": "sea-1", "name": "Vessel Alpha", "lat": 28.8, "lng": 149.6},
                        {"id": "sea-2", "name": "Vessel Bravo", "lat": 42.0, "lng": -158.3},
                        {"id": "sea-3", "name": "Vessel Charlie", "lat": 36.2, "lng": 34.5},
                    ],
                },
                "regional": {
                    "ports": [
                        {"name": "Los Angeles DC", "lat": 34.05, "lng": -118.24, "risk": 10},
                        {"name": "Chicago DC", "lat": 41.87, "lng": -87.62, "risk": 25},
                        {"name": "Newark Hub", "lat": 40.69, "lng": -74.17, "risk": 5},
                    ],
                    "assets": [
                        {"id": "land-1", "name": "Truck 405A", "lat": 38.8, "lng": -104.8},
                        {"id": "land-2", "name": "Truck 102B", "lat": 41.1, "lng": -96.0},
                        {"id": "land-3", "name": "Truck 202C", "lat": 35.6, "lng": -106.4},
                    ],
                },
                "airFreight": {
                    "ports": [
                        {"name": "Anchorage", "lat": 61.17, "lng": -149.99, "risk": 10},
                        {"name": "LAX", "lat": 33.94, "lng": -118.4, "risk": 20},
                        {"name": "Frankfurt", "lat": 50.03, "lng": 8.57, "risk": 10},
                    ],
                    "assets": self._generate_air_freight_assets(),
                },
            },
        }

    def trigger_event(self, map_view: str):
        state = self.get_state()
        event_text = f"Simulated event injected for view '{map_view}'."
        state["alerts"]["global"].insert(0, {"type": "critical", "text": event_text})
        return state

    def simulate(self, scenario: str, optimize: bool):
        state = self.get_state()
        if scenario == "port-strike":
            state["kpis"]["lostSales"]["value"] = "$4.2M"
            state["alerts"]["global"].insert(
                0,
                {
                    "type": "critical",
                    "text": "SIMULATION: Port Strike impact high. Rerouting recommended.",
                },
            )
        elif scenario == "geopolitical":
            state["kpis"]["turnover"]["value"] = "3.1x"
            state["alerts"]["global"].insert(
                0, {"type": "critical", "text": "SIMULATION: Suez blockage. 14-day delay."}
            )

        state["performance"] = {
            "mode": "Distributed (vLLM)" if optimize else "Standard Monolithic",
            "cacheRate": "93%" if optimize else "0%",
            "latency": "0.42s" if optimize else "3.10s",
            "costSavings": "52%" if optimize else "0%",
            "totalTokens": "3800",
            "tokensPerSecond": "126 t/s" if optimize else "19 t/s",
        }
        return state
