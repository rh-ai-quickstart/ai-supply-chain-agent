"""Atomic JSON-file-backed append-only store (demo persistence; ephemeral).

Extracted from near-identical store helpers (``suggestions.md`` debt M3).
Data is lost on container restart unless the configured path is on a persistent
volume — this is intentionally a demo backend; see ``KnowledgeBaseRepository``.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any


class JsonFileStore:
    """Thread-safe atomic read/write of a JSON list of records at ``path``."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()

    @property
    def path(self) -> str:
        return self._path

    def load_all(self) -> list[dict[str, Any]]:
        with self._lock:
            return self._load_unlocked()

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            items = self._load_unlocked()
            items.append(record)
            self._write_unlocked(items)
            return record

    def _load_unlocked(self) -> list[dict[str, Any]]:
        if not os.path.isfile(self._path):
            return []
        with open(self._path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []

    def _write_unlocked(self, items: list[dict[str, Any]]) -> None:
        parent = os.path.dirname(self._path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp_path = f"{self._path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(items, handle, indent=2)
        os.replace(tmp_path, self._path)
