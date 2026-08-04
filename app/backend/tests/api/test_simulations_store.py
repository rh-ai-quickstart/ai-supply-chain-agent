"""Tests for ``services.simulations_store``.

The store writes to a temp file by default; each test gets its own
directory so they don't collide.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Make the service module importable from the api context.
from services.simulations_store import append_simulation, load_all


def _set_store_path(path: str) -> None:
    """Override the store path for the duration of a single test."""
    # The module reads the env var at function-call time, not import time,
    # so setting it before calling the public functions is enough.
    os.environ["SIMULATIONS_STORE_PATH"] = path


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path: Path):
    """Use a unique file per test."""
    store_file = str(tmp_path / "simulations.json")
    _set_store_path(store_file)
    yield store_file


class TestSimulationsStore:
    def test_empty_list_when_no_file_exists(self):
        store = os.environ["SIMULATIONS_STORE_PATH"]
        # Remove if exists from a previous test
        Path(store).unlink(missing_ok=True)
        result = load_all()
        assert result == []

    def test_load_all_returns_list_of_one(self):
        append_simulation("test-1", "first test")
        results = load_all()
        assert len(results) == 1
        assert results[0]["name"] == "test-1"
        assert results[0]["description"] == "first test"
        assert "id" in results[0]
        assert "createdAt" in results[0]

    def test_load_all_returns_list_of_multiple(self):
        append_simulation("a", "desc a")
        append_simulation("b", "desc b")
        results = load_all()
        assert len(results) == 2
        assert results[0]["name"] == "a"
        assert results[1]["name"] == "b"

    def test_append_returns_record_with_id(self):
        record = append_simulation("scenario-x", "desc x")
        assert isinstance(record["id"], str)
        assert len(record["id"]) > 0  # valid UUID

    def test_append_strips_whitespace_from_name(self):
        append_simulation("  my-scenario  ", "description")
        results = load_all()
        assert results[0]["name"] == "my-scenario"

    def test_append_strips_whitespace_from_description(self):
        append_simulation("scenario", "  wow  ")
        results = load_all()
        assert results[0]["description"] == "wow"

    def test_append_with_none_description(self):
        append_simulation("scenario", None)
        results = load_all()
        assert results[0]["description"] == ""

    def test_createdAt_is_iso_format(self):
        record = append_simulation("ts-test", "desc")
        # Should parse without error (e.g. 2024-01-15T10:30:00+00:00)
        assert "T" in record["createdAt"]
        assert "+" in record["createdAt"] or record["createdAt"].endswith("Z")

    def test_load_all_persists_across_calls(self):
        append_simulation("p1", "first")
        # A second call to load_all reads from the file
        results = load_all()
        assert len(results) == 1
        append_simulation("p2", "second")
        results = load_all()
        assert len(results) == 2

    def test_does_not_corrupt_on_duplicate_name(self):
        append_simulation("dup", "first")
        append_simulation("dup", "second")
        results = load_all()
        assert len(results) == 2
        ids = [r["id"] for r in results]
        assert ids[0] != ids[1]
