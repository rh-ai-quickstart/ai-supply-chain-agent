"""``SimulationRepository`` catalog behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from repositories.simulation_repository import SimulationRepository


@pytest.fixture
def repo(tmp_path: Path) -> SimulationRepository:
    return SimulationRepository(str(tmp_path / "simulations.json"))


def test_empty_list_when_no_file_exists(repo: SimulationRepository):
    assert repo.load_all() == []


def test_load_all_returns_list_of_one(repo: SimulationRepository):
    repo.append_simulation("test-1", "first test")
    results = repo.load_all()
    assert len(results) == 1
    assert results[0]["name"] == "test-1"
    assert results[0]["description"] == "first test"
    assert "id" in results[0]
    assert "createdAt" in results[0]


def test_load_all_returns_list_of_multiple(repo: SimulationRepository):
    repo.append_simulation("a", "desc a")
    repo.append_simulation("b", "desc b")
    results = repo.load_all()
    assert len(results) == 2
    assert results[0]["name"] == "a"
    assert results[1]["name"] == "b"


def test_append_returns_record_with_id(repo: SimulationRepository):
    record = repo.append_simulation("scenario-x", "desc x")
    assert isinstance(record["id"], str)
    assert len(record["id"]) > 0


def test_append_strips_whitespace_from_name_and_description(repo: SimulationRepository):
    repo.append_simulation("  my-scenario  ", "  wow  ")
    results = repo.load_all()
    assert results[0]["name"] == "my-scenario"
    assert results[0]["description"] == "wow"


def test_append_with_none_description(repo: SimulationRepository):
    repo.append_simulation("scenario", None)
    results = repo.load_all()
    assert results[0]["description"] == ""


def test_created_at_is_iso_format(repo: SimulationRepository):
    record = repo.append_simulation("ts-test", "desc")
    assert "T" in record["createdAt"]
    assert "+" in record["createdAt"] or record["createdAt"].endswith("Z")


def test_load_all_persists_across_calls(repo: SimulationRepository):
    repo.append_simulation("p1", "first")
    assert len(repo.load_all()) == 1
    repo.append_simulation("p2", "second")
    assert len(repo.load_all()) == 2


def test_does_not_corrupt_on_duplicate_name(repo: SimulationRepository):
    repo.append_simulation("dup", "first")
    repo.append_simulation("dup", "second")
    results = repo.load_all()
    assert len(results) == 2
    ids = [r["id"] for r in results]
    assert ids[0] != ids[1]
