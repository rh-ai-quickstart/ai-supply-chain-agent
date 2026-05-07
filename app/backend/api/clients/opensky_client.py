"""Cached HTTP client for OpenSky Network aircraft state (legacy app parity)."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class OpenSkyClient:
    """Fetches `/api/states/all` with a short-lived in-memory cache."""

    OPEN_SKY_URL = "https://opensky-network.org/api/states/all"
    CACHE_DURATION_SECONDS = 360

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()
        self._lock = threading.Lock()
        self._cached_states: list[Any] | None = None
        self._last_fetch: float = 0.0

    def fetch_states(self) -> list[Any] | None:
        """Return latest state vectors, or stale cache on failure, or None."""
        with self._lock:
            now = time.time()
            if (
                self._cached_states is not None
                and (now - self._last_fetch) < self.CACHE_DURATION_SECONDS
            ):
                return self._cached_states

        try:
            logger.info("OpenSkyClient: requesting %s", self.OPEN_SKY_URL)
            response = self._session.get(self.OPEN_SKY_URL, timeout=8)
            if response.status_code == 200:
                data = response.json()
                states = data.get("states", [])
                with self._lock:
                    self._cached_states = states
                    self._last_fetch = time.time()
                    logger.info("OpenSkyClient: cached %s flights", len(states))
                return states
            logger.warning(
                "OpenSkyClient: HTTP %s (using cache if present)",
                response.status_code,
            )
        except Exception as exc:
            logger.warning("OpenSkyClient: error %s (using cache if present)", exc)

        with self._lock:
            return self._cached_states
