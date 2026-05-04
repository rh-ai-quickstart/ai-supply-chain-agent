"""Ephemeral JSON file store for demo simulations (lost on container restart)."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()
_DEFAULT_PATH = "/tmp/supply-chain-simulations.json"


def _store_path() -> str:
    return os.environ.get("SIMULATIONS_STORE_PATH", _DEFAULT_PATH)


def _load_unlocked() -> list[dict[str, Any]]:
    path = _store_path()
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else []


def _write_unlocked(items: list[dict[str, Any]]) -> None:
    path = _store_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(items, handle, indent=2)
    os.replace(tmp_path, path)


def load_all() -> list[dict[str, Any]]:
    with _lock:
        return _load_unlocked()


def append_simulation(name: str, description: str) -> dict[str, Any]:
    with _lock:
        items = _load_unlocked()
        record = {
            "id": str(uuid.uuid4()),
            "name": name.strip(),
            "description": (description or "").strip(),
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        items.append(record)
        _write_unlocked(items)
        return record
