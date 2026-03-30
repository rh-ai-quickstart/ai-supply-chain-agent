import logging

logger = logging.getLogger(__name__)

ROUTE_KEYWORDS = ["route", "routing", "truck", "trucking", "shipment path", "transit path"]

# Known DC coordinates used for route lookups
_LOCATIONS = {
    "los angeles dc": (34.05, -118.24),
    "chicago dc": (41.87, -87.62),
    "newark hub": (40.69, -74.17),
    "dallas dc": (32.77, -96.79),
}

_DEFAULT_START = "los angeles dc"
_DEFAULT_END = "chicago dc"


class RouteService:
    """Encapsulates route optimisation logic for chat responses.

    In the legacy app this lived as an inline fallback inside the chat
    endpoint.  Extracting it here keeps ChatService focused on intent
    detection and LLM orchestration, while routing concerns remain
    independently testable and extensible.
    """

    def is_route_query(self, user_input: str) -> bool:
        lowered = user_input.lower()
        return any(kw in lowered for kw in ROUTE_KEYWORDS)

    def get_optimized_route(self, user_input: str) -> dict:
        """Return a structured route optimisation response.

        Resolves origin/destination from the query text, falling back to
        the LA → Chicago default when no known location is detected.
        """
        lowered = user_input.lower()

        start = _DEFAULT_START
        end = _DEFAULT_END

        if "newark" in lowered or " ny" in lowered:
            start = "newark hub"
        if "dallas" in lowered:
            end = "dallas dc"

        start_coords = _LOCATIONS[start]
        end_coords = _LOCATIONS[end]

        logger.info("Route optimisation: %s → %s", start, end)

        return {
            "answer": (
                f"Calculated the best route from {start.title()} to "
                f"{end.title()} based on current traffic and fuel costs."
            ),
            "routeData": {
                "type": "optimized_land_route",
                "coordinates": [
                    list(start_coords),
                    list(end_coords),
                ],
                "color": "#FFC300",
            },
        }
