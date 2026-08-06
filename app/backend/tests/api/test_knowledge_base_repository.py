"""``KnowledgeBaseRepository`` catalog behavior."""

from __future__ import annotations

from pathlib import Path

from repositories.knowledge_base_repository import KnowledgeBaseRepository, new_record_stub


def test_load_all_empty_by_default(tmp_path: Path):
    repo = KnowledgeBaseRepository(str(tmp_path / "kb.json"))
    assert repo.load_all() == []


def test_append_upload_creates_record_and_persists(tmp_path: Path):
    repo = KnowledgeBaseRepository(str(tmp_path / "kb.json"))
    record = repo.append_upload(
        name=" Docs ",
        vector_store_id="vs_1",
        files_meta=[{"filename": "a.txt", "file_id": "f1", "bytes": 5}],
    )
    assert record["name"] == "Docs"
    assert record["vector_store_id"] == "vs_1"
    assert "id" in record and "createdAt" in record
    assert repo.load_all() == [record]


def test_append_raw_record(tmp_path: Path):
    repo = KnowledgeBaseRepository(str(tmp_path / "kb.json"))
    row = new_record_stub(name="A", vector_store_id="vs1", files_meta=[])
    repo.append(row)
    loaded = repo.load_all()
    assert len(loaded) == 1
    assert loaded[0]["name"] == "A"
