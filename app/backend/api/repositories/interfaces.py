"""Repository seam: decouples services from the JSON-file persistence detail.

Callers depend on this ``Protocol``, not on ``JsonFileStore`` directly, so a
future ``SqlKnowledgeBaseRepository`` (or any other backend) can be swapped in
at the composition root with zero changes to service code (Dependency
Inversion).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Repository(Protocol):
    """A simple append-only catalog of JSON-serializable records."""

    def load_all(self) -> list[dict[str, Any]]: ...

    def append(self, record: dict[str, Any]) -> dict[str, Any]: ...
