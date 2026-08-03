"""``LlamaStackIngestionService`` single-store-per-KB loop (mocked LlamaStack client)."""

import openai
from unittest.mock import MagicMock, call

import pytest

from config import IngestConfig, IngestionStrategy
from services.llamastack_ingestion_service import (
    LlamaStackIngestionService,
    _vector_store_name_for_kb,
)


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
    client.create_vector_store.return_value = "vs1"
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


def test_run_creates_single_store_for_whole_kb(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "one.txt").write_text("hello", encoding="utf-8")
    (kb / "two.txt").write_text("world", encoding="utf-8")
    (kb / "three.txt").write_text("again", encoding="utf-8")

    client = MagicMock()
    client.create_vector_store.return_value = "vs1"
    client.upload_file.side_effect = ["f1", "f2", "f3"]

    svc = LlamaStackIngestionService(client)
    cfg = IngestConfig(
        strategy=IngestionStrategy.LLAMASTACK,
        knowledge_base_dir=str(kb),
        glob="*.txt",
    )
    n = svc.run(cfg)

    assert n == 3
    # One create_vector_store call for the whole knowledge base.
    assert client.create_vector_store.call_count == 1
    # Store name is derived from the KB directory basename.
    (args, _) = client.create_vector_store.call_args
    assert args[0].startswith("kb-")

    # Every file is uploaded and attached to that same store id.
    assert client.upload_file.call_count == 3
    assert client.attach_file_to_store.call_count == 3
    expected_attaches = [call("vs1", "f1"), call("vs1", "f2"), call("vs1", "f3")]
    assert client.attach_file_to_store.call_args_list == expected_attaches


def test_run_uploads_all_files_with_source_filename_metadata(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "one.txt").write_text("hello", encoding="utf-8")
    (kb / "two.txt").write_text("world", encoding="utf-8")

    client = MagicMock()
    client.create_vector_store.return_value = "vs1"
    client.upload_file.side_effect = ["f1", "f2"]

    svc = LlamaStackIngestionService(client)
    cfg = IngestConfig(
        strategy=IngestionStrategy.LLAMASTACK,
        knowledge_base_dir=str(kb),
        glob="*.txt",
    )
    svc.run(cfg)

    expected_uploads = [
        call(str(kb / "one.txt"), source_filename="one.txt"),
        call(str(kb / "two.txt"), source_filename="two.txt"),
    ]
    assert client.upload_file.call_args_list == expected_uploads


def test_run_returns_zero_when_store_creation_fails(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "one.txt").write_text("hello", encoding="utf-8")

    client = MagicMock()
    client.create_vector_store.side_effect = openai.APIError(
        "boom", request=None, body=None
    )

    svc = LlamaStackIngestionService(client)
    cfg = IngestConfig(
        strategy=IngestionStrategy.LLAMASTACK,
        knowledge_base_dir=str(kb),
        glob="*.txt",
    )
    n = svc.run(cfg)
    assert n == 0
    assert client.upload_file.call_count == 0
    assert client.attach_file_to_store.call_count == 0


def test_vector_store_name_for_kb_unique_per_run(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    first = _vector_store_name_for_kb(kb)
    second = _vector_store_name_for_kb(kb)
    assert first.startswith("kb-")
    assert first != second
