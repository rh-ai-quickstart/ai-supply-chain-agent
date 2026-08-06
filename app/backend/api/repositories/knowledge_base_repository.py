"""Repository for the UI-upload knowledge-base catalog (demo JSON persistence)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from repositories.json_file_store import JsonFileStore

DEFAULT_PATH = "/tmp/supply-chain-knowledge-bases.json"


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


class KnowledgeBaseRepository:
    """Catalog of knowledge bases created from the UI upload flow."""

    def __init__(self, path: str = DEFAULT_PATH, *, store: JsonFileStore | None = None) -> None:
        self._store = store or JsonFileStore(path)

    def load_all(self) -> list[dict[str, Any]]:
        return self._store.load_all()

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._store.append(record)

    def append_upload(
        self,
        *,
        name: str,
        vector_store_id: str,
        files_meta: list[dict[str, Any]],
    ) -> dict[str, Any]:
        record = new_record_stub(name=name, vector_store_id=vector_store_id, files_meta=files_meta)
        return self._store.append(record)
