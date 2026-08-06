"""``ReadinessService`` downstream-dependency checks."""

from unittest.mock import MagicMock

from services.readiness_service import ReadinessService


def _make(llama=None, general_sim=None, vector_store=None):
    return ReadinessService(
        llama or MagicMock(),
        general_sim or MagicMock(),
        vector_store,
    )


def test_ready_when_all_dependencies_healthy():
    llama = MagicMock()
    general_sim = MagicMock()
    general_sim.health.return_value = {"status": "ok"}
    service = _make(llama, general_sim, vector_store=MagicMock())
    out = service.check()
    assert out["ready"] is True
    assert out["checks"]["llama_stack"]["ok"] is True
    assert out["checks"]["general_simulation"]["ok"] is True
    assert out["checks"]["pgvector"]["ok"] is True


def test_not_ready_when_llama_stack_raises():
    llama = MagicMock()
    llama.list_vector_stores.side_effect = RuntimeError("down")
    general_sim = MagicMock()
    general_sim.health.return_value = {"status": "ok"}
    service = _make(llama, general_sim, vector_store=MagicMock())
    out = service.check()
    assert out["ready"] is False
    assert out["checks"]["llama_stack"]["ok"] is False
    assert "down" in out["checks"]["llama_stack"]["error"]


def test_not_ready_when_general_simulation_unreachable():
    general_sim = MagicMock()
    general_sim.health.return_value = {"status": "unreachable", "db": "unknown"}
    service = _make(general_sim=general_sim, vector_store=MagicMock())
    out = service.check()
    assert out["ready"] is False
    assert out["checks"]["general_simulation"]["ok"] is False


def test_not_ready_when_pgvector_not_configured():
    service = _make(vector_store=None)
    out = service.check()
    assert out["ready"] is False
    assert out["checks"]["pgvector"]["ok"] is False
