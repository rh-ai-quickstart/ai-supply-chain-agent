"""``LlamaStackIngestionService`` file loop (mocked LlamaStack client)."""

from unittest.mock import MagicMock

import pytest

from config import IngestConfig, IngestionStrategy
from services.llamastack_ingestion_service import LlamaStackIngestionService


def test_run_raises_when_directory_missing(tmp_path):
    client = MagicMock()
    svc = LlamaStackIngestionService(client)
    cfg = IngestConfig(
        strategy=IngestionStrategy.LLAMASTACK,
        knowledge_base_dir=str(tmp_path / "missing"),
        glob="**/*.txt",
    )
    with pytest.raises(FileNotFoundError):
        svc.run(cfg)


def test_run_counts_successful_uploads(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "one.txt").write_text("hello", encoding="utf-8")
    (kb / "two.txt").write_text("world", encoding="utf-8")

    client = MagicMock()
    client.create_vector_store.side_effect = ["vs1", "vs2"]
    client.upload_file.side_effect = ["f1", "f2"]

    svc = LlamaStackIngestionService(client)
    cfg = IngestConfig(
        strategy=IngestionStrategy.LLAMASTACK,
        knowledge_base_dir=str(kb),
        glob="*.txt",
    )
    n = svc.run(cfg)
    assert n == 2
    assert client.attach_file_to_store.call_count == 2
