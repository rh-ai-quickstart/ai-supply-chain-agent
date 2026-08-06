"""Live cargo/general flight tracking (SRP split out of ``supply_chain_state_builder.py``).

Normalizes OpenSky state vectors into UI-ready flight dicts. Replaces the
previous bare ``except (...): continue`` per-flight swallow with structured
error telemetry (``suggestions.md`` debt M6) so malformed state vectors are
visible in logs/metrics instead of disappearing silently.
"""

from __future__ import annotations

import logging
from typing import Any

from clients.opensky_client import OpenSkyClient

logger = logging.getLogger(__name__)

_GENERAL_CARGO_MIN_VELOCITY = 100
_TARGET_DENSITY = 100
_STATE_VECTOR_ERRORS = (AttributeError, IndexError, TypeError)


class FlightTrackingService:
    """Fetches OpenSky state vectors and normalizes them into display-ready flights."""

    def __init__(self, opensky_client: OpenSkyClient, cargo_watchlist: list[str]):
        self._opensky = opensky_client
        self._cargo_watchlist = cargo_watchlist
        self.skipped_count = 0

    def get_live_planes(self, *, target_density: int = _TARGET_DENSITY) -> list[dict[str, Any]]:
        """Return normalized live flights, or ``[]`` if OpenSky has no data."""
        live_states = self._opensky.fetch_states()
        if not live_states:
            return []

        self.skipped_count = 0
        live_planes = self._match_cargo_watchlist(live_states)
        if len(live_planes) < target_density:
            self._fill_with_general_traffic(live_states, live_planes, target_density)
        return live_planes

    def _match_cargo_watchlist(self, live_states: list[Any]) -> list[dict[str, Any]]:
        live_planes: list[dict[str, Any]] = []
        for state in live_states:
            plane = self._normalize_cargo_state(state)
            if plane is not None:
                live_planes.append(plane)
        return live_planes

    def _normalize_cargo_state(self, state: Any) -> dict[str, Any] | None:
        try:
            if state[8]:
                return None
            callsign = state[1].strip() if state[1] else ""
            if not any(callsign.startswith(prefix) for prefix in self._cargo_watchlist):
                return None
            velocity = state[9] if state[9] is not None else 0
            altitude = state[7] if state[7] is not None else 0
            return {
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
        except _STATE_VECTOR_ERRORS as exc:
            self._record_skipped(state, exc)
            return None

    def _fill_with_general_traffic(
        self,
        live_states: list[Any],
        live_planes: list[dict[str, Any]],
        target_density: int,
    ) -> None:
        seen_ids = {plane["id"] for plane in live_planes}
        for state in live_states:
            if len(live_planes) >= target_density:
                break
            plane = self._normalize_general_state(state, seen_ids)
            if plane is not None:
                live_planes.append(plane)
                seen_ids.add(plane["id"])

    def _normalize_general_state(
        self, state: Any, seen_ids: set[Any]
    ) -> dict[str, Any] | None:
        try:
            if state[8] or state[0] in seen_ids:
                return None
            if not (state[9] and state[9] > _GENERAL_CARGO_MIN_VELOCITY):
                return None
            callsign = state[1].strip() if state[1] else "FLIGHT"
            altitude = state[7] if state[7] is not None else 0
            return {
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
        except _STATE_VECTOR_ERRORS as exc:
            self._record_skipped(state, exc)
            return None

    def _record_skipped(self, state: Any, exc: Exception) -> None:
        self.skipped_count += 1
        logger.warning(
            "FlightTrackingService: skipped malformed OpenSky state vector (%s: %s) state=%r",
            type(exc).__name__,
            exc,
            state,
        )
