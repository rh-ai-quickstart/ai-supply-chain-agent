"""``JsonFileStore`` atomic read/write behavior."""

from __future__ import annotations

from pathlib import Path

from repositories.json_file_store import JsonFileStore


def test_load_all_returns_empty_list_when_file_missing(tmp_path: Path):
    store = JsonFileStore(str(tmp_path / "missing.json"))
    assert store.load_all() == []


def test_append_persists_and_creates_parent_dirs(tmp_path: Path):
    path = tmp_path / "nested" / "store.json"
    store = JsonFileStore(str(path))
    record = store.append({"id": "1", "name": "A"})
    assert record == {"id": "1", "name": "A"}
    assert path.is_file()


def test_append_accumulates_across_calls(tmp_path: Path):
    store = JsonFileStore(str(tmp_path / "store.json"))
    store.append({"id": "1"})
    store.append({"id": "2"})
    assert [r["id"] for r in store.load_all()] == ["1", "2"]


def test_load_all_ignores_non_list_contents(tmp_path: Path):
    path = tmp_path / "store.json"
    path.write_text('{"not": "a list"}', encoding="utf-8")
    store = JsonFileStore(str(path))
    assert store.load_all() == []


def test_two_stores_at_same_path_share_state(tmp_path: Path):
    path = str(tmp_path / "shared.json")
    store_a = JsonFileStore(path)
    store_b = JsonFileStore(path)
    store_a.append({"id": "1"})
    assert store_b.load_all() == [{"id": "1"}]
