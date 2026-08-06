"""Repository for the demo "simulations" catalog (demo JSON persistence)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from repositories.json_file_store import JsonFileStore

DEFAULT_PATH = "/tmp/supply-chain-simulations.json"


class SimulationRepository:
    """Catalog of named simulation runs recorded from the UI."""

    def __init__(self, path: str = DEFAULT_PATH, *, store: JsonFileStore | None = None) -> None:
        self._store = store or JsonFileStore(path)

    def load_all(self) -> list[dict[str, Any]]:
        return self._store.load_all()

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._store.append(record)

    def append_simulation(self, name: str, description: str) -> dict[str, Any]:
        record = {
            "id": str(uuid.uuid4()),
            "name": name.strip(),
            "description": (description or "").strip(),
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        return self._store.append(record)
