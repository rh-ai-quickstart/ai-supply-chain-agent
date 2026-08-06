"""Aggregate downstream-dependency reachability for ``/readyz``.

Addresses ``suggestions.md`` debt L8 ("add health check endpoints") without
changing the existing ``/healthz`` liveness probe's response shape.
"""

from __future__ import annotations

from typing import Any, Optional


class ReadinessService:
    def __init__(
        self,
        llama_stack_client: Any,
        general_simulation_client: Any,
        vector_store_client: Optional[Any] = None,
    ) -> None:
        self._llama = llama_stack_client
        self._general_sim = general_simulation_client
        self._vector_store_client = vector_store_client

    def check(self) -> dict[str, Any]:
        checks = {
            "llama_stack": self._check_llama_stack(),
            "general_simulation": self._check_general_simulation(),
            "pgvector": self._check_pgvector(),
        }
        return {"ready": all(c["ok"] for c in checks.values()), "checks": checks}

    def _check_llama_stack(self) -> dict[str, Any]:
        try:
            self._llama.list_vector_stores()
            return {"ok": True}
        # Broad catch: reachability probe should never raise into the /readyz route.
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _check_general_simulation(self) -> dict[str, Any]:
        try:
            result = self._general_sim.health()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        status = result.get("status")
        return {"ok": status not in (None, "unreachable"), "detail": result}

    def _check_pgvector(self) -> dict[str, Any]:
        if self._vector_store_client is None:
            return {"ok": False, "error": "PGVector client not configured"}
        return {"ok": True}
