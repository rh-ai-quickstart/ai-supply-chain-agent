"""``LlamaStackIngestionService`` one-store-per-file loop (mocked LlamaStack client)."""

import openai
from unittest.mock import MagicMock, call

import pytest

from config import IngestConfig, IngestionStrategy
from services.llamastack_ingestion_service import (
    LlamaStackIngestionService,
    _vector_store_name_for_file,
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


def test_run_creates_one_store_per_file(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "air_risk_uk_nats_gps_closure.txt").write_text("uk", encoding="utf-8")
    (kb / "land_risk_port_strike_la.txt").write_text("port", encoding="utf-8")
    (kb / "suez_blockage_analysis.txt").write_text("suez", encoding="utf-8")

    client = MagicMock()
    client.create_vector_store.side_effect = ["vs1", "vs2", "vs3"]
    client.upload_file.side_effect = ["f1", "f2", "f3"]

    svc = LlamaStackIngestionService(client)
    cfg = IngestConfig(
        strategy=IngestionStrategy.LLAMASTACK,
        knowledge_base_dir=str(kb),
        glob="*.txt",
    )
    n = svc.run(cfg)

    assert n == 3
    assert client.create_vector_store.call_count == 3
    store_names = [args[0] for args, _ in client.create_vector_store.call_args_list]
    assert store_names[0].startswith("air_risk_uk_nats_gps_closure-")
    assert store_names[1].startswith("land_risk_port_strike_la-")
    assert store_names[2].startswith("suez_blockage_analysis-")

    assert client.upload_file.call_count == 3
    assert client.attach_file_to_store.call_count == 3
    expected_attaches = [
        call("vs1", "f1"),
        call("vs2", "f2"),
        call("vs3", "f3"),
    ]
    assert client.attach_file_to_store.call_args_list == expected_attaches


def test_run_uploads_all_files_with_source_filename_metadata(tmp_path):
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
    svc.run(cfg)

    expected_uploads = [
        call(str(kb / "one.txt"), source_filename="one.txt"),
        call(str(kb / "two.txt"), source_filename="two.txt"),
    ]
    assert client.upload_file.call_args_list == expected_uploads


def test_run_returns_zero_when_all_store_creations_fail(tmp_path):
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


def test_run_cleans_up_store_when_upload_fails(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "one.txt").write_text("hello", encoding="utf-8")

    client = MagicMock()
    client.create_vector_store.return_value = "vs1"
    client.upload_file.side_effect = openai.APIError("upload failed", request=None, body=None)

    svc = LlamaStackIngestionService(client)
    cfg = IngestConfig(
        strategy=IngestionStrategy.LLAMASTACK,
        knowledge_base_dir=str(kb),
        glob="*.txt",
    )
    n = svc.run(cfg)
    assert n == 0
    client.delete_vector_store.assert_called_once_with("vs1")


def test_vector_store_name_for_file_unique_per_run(tmp_path):
    path = tmp_path / "air_risk_uk_nats_gps_closure.txt"
    path.write_text("x", encoding="utf-8")
    first = _vector_store_name_for_file(path)
    second = _vector_store_name_for_file(path)
    assert first.startswith("air_risk_uk_nats_gps_closure-")
    assert first != second
