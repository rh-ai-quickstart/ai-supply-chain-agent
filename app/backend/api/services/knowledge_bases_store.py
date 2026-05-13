"""JSON file catalog for knowledge bases created from the UI (demo; path overridable via env)."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()
_DEFAULT_PATH = "/tmp/supply-chain-knowledge-bases.json"


def _store_path() -> str:
    return os.environ.get("KNOWLEDGE_BASES_STORE_PATH", _DEFAULT_PATH)


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


def append_record(record: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        items = _load_unlocked()
        items.append(record)
        _write_unlocked(items)
        return record


def new_record_stub(
    *,
    name: str,
    vector_store_id: str,
    files_meta: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "vector_store_id": vector_store_id,
        "files": files_meta,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
