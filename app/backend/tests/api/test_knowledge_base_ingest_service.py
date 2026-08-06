"""Tests for upload validation and ingest orchestration (mocked LlamaStack)."""

from unittest.mock import MagicMock

from services.knowledge_base_ingest_service import _vector_store_slug, ingest_uploaded_files


def test_vector_store_slug_sanitizes():
    assert _vector_store_slug("My KB #1!") == "My-KB-1"


def test_ingest_requires_name():
    llama = MagicMock()
    out = ingest_uploaded_files(llama, "  ", [("a.txt", b"x")])
    assert out["ok"] is False
    assert "name" in out["error"]


def test_ingest_requires_files():
    llama = MagicMock()
    out = ingest_uploaded_files(llama, "KB", [])
    assert out["ok"] is False


def test_ingest_skips_unsupported_types():
    llama = MagicMock()
    out = ingest_uploaded_files(
        llama,
        "KB",
        [("readme.exe", b"data")],
    )
    assert out["ok"] is False
    assert "warnings" in out


def test_ingest_success_appends_catalog(mock_llama_stack_client):
    mock_llama_stack_client.create_vector_store.return_value = "vs_99"
    mock_llama_stack_client.upload_file_bytes.return_value = "f1"
    repo = MagicMock()
    repo.append_upload.return_value = {"id": "kb1", "vector_store_id": "vs_99"}

    out = ingest_uploaded_files(
        mock_llama_stack_client,
        "My Catalog",
        [("notes.txt", b"hello world")],
        repository=repo,
    )
    assert out["ok"] is True
    assert out["knowledge_base"]["vector_store_id"] == "vs_99"
    repo.append_upload.assert_called_once()
    mock_llama_stack_client.attach_file_to_vector_store.assert_called_once_with(
        "vs_99", "f1"
    )


def test_ingest_create_store_failure():
    llama = MagicMock()
    llama.create_vector_store.side_effect = RuntimeError("upstream down")
    out = ingest_uploaded_files(llama, "KB", [("a.txt", b"ok")])
    assert out["ok"] is False
    assert "upstream" in out["error"]


def test_ingest_upload_failure_cleans_up_store(mock_llama_stack_client):
    """Upload fails partway through — store must be deleted on cleanup."""
    mock_llama_stack_client.create_vector_store.return_value = "vs_99"
    mock_llama_stack_client.upload_file_bytes.side_effect = RuntimeError("network error")

    out = ingest_uploaded_files(
        mock_llama_stack_client,
        "My Catalog",
        [("a.txt", b"hello"), ("b.txt", b"world")],
    )
    assert out["ok"] is False
    assert out["error"] == "network error"
    assert out["vector_store_id"] == "vs_99"
    mock_llama_stack_client.delete_vector_store.assert_called_once_with("vs_99")


def test_ingest_attach_failure_cleans_up_store(mock_llama_stack_client):
    """Attach fails partway through — all files uploaded but attach fails."""
    mock_llama_stack_client.create_vector_store.return_value = "vs_99"
    mock_llama_stack_client.upload_file_bytes.side_effect = ["file_1", RuntimeError("attach broke")]

    out = ingest_uploaded_files(
        mock_llama_stack_client,
        "My Catalog",
        [("a.txt", b"hello"), ("b.txt", b"world")],
    )
    assert out["ok"] is False
    assert out["error"] == "attach broke"
    assert out["vector_store_id"] == "vs_99"
    mock_llama_stack_client.delete_vector_store.assert_called_once_with("vs_99")
