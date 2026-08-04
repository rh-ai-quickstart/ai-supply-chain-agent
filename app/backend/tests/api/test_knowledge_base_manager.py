"""Tests for ``services.knowledge_base_manager``."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.knowledge_base_manager import KnowledgeBaseManager


def _make_mock_llama_client() -> MagicMock:
    """Build a LlamaStackClient mock configured for happy-path registration."""
    client = MagicMock()
    mock_vs = MagicMock()
    mock_vs.id = "vs_abc123"
    client.vector_stores.create.return_value = mock_vs

    mock_file = MagicMock()
    mock_file.id = "file_xyz"
    client.files.create.return_value = mock_file
    client.vector_stores.files = MagicMock()

    return client


@pytest.fixture
def _mock_logger():
    """Mock the module-level logger so kwargs like kb_name= don't raise TypeError."""
    with patch("services.knowledge_base_manager.logger", MagicMock()):
        yield


class TestKnowledgeBaseManagerConnectToLlamastackClient:
    @patch("services.knowledge_base_manager.LlamaStackClient")
    def test_creates_client_when_none(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        manager = KnowledgeBaseManager.__new__(KnowledgeBaseManager)
        manager._llama_client = None
        manager.connect_to_llamastack_client()
        assert manager._llama_client is mock_client

    @patch("services.knowledge_base_manager.LlamaStackClient")
    def test_does_nothing_when_already_connected(self, mock_client_cls):
        existing = MagicMock()
        manager = KnowledgeBaseManager.__new__(KnowledgeBaseManager)
        manager._llama_client = existing
        manager.connect_to_llamastack_client()
        assert manager._llama_client is existing
        mock_client_cls.assert_not_called()

    def test_creates_new_client_via_init(self):
        manager = KnowledgeBaseManager(MagicMock())
        manager.connect_to_llamastack_client()
        assert manager._llama_client is not None


class TestKnowledgeBaseManagerRegisterKnowledgeBases:
    @pytest.mark.usefixtures("_mock_logger")
    def test_returns_true_when_path_does_not_exist(self):
        manager = KnowledgeBaseManager(_make_mock_llama_client())
        manager._knowledge_bases_path = Path("/nonexistent/path/xyz")
        result = manager.register_knowledge_bases()
        assert result is True

    @pytest.mark.usefixtures("_mock_logger")
    def test_single_directory_registered(self, tmp_path):
        kb_dir = tmp_path / "test-kb"
        kb_dir.mkdir()

        manager = KnowledgeBaseManager(_make_mock_llama_client())
        manager._knowledge_bases_path = tmp_path
        result = manager.register_knowledge_bases()
        assert result is True

    @pytest.mark.usefixtures("_mock_logger")
    def test_returns_false_when_one_fails(self, tmp_path, monkeypatch):
        sub1 = tmp_path / "kb-ok"
        sub2 = tmp_path / "kb-bad"
        sub1.mkdir()
        sub2.mkdir()

        manager = KnowledgeBaseManager(_make_mock_llama_client())
        manager._knowledge_bases_path = tmp_path

        original_register = KnowledgeBaseManager.register_knowledge_base

        def patched_register(self, kb_directory: Path):
            return "vs_123" if "ok" in kb_directory.name else None

        monkeypatch.setattr(
            KnowledgeBaseManager,
            "register_knowledge_base",
            patched_register,
        )
        result = manager.register_knowledge_bases()
        assert result is False

    @pytest.mark.usefixtures("_mock_logger")
    def test_uses_pgvector_provider_id(self, tmp_path):
        kb_dir = tmp_path / "my-kb"
        kb_dir.mkdir()

        manager = KnowledgeBaseManager(_make_mock_llama_client())
        manager._knowledge_bases_path = tmp_path
        manager.register_knowledge_bases()
        manager._llama_client.vector_stores.create.assert_called_once()
        call_kwargs = manager._llama_client.vector_stores.create.call_args
        assert call_kwargs[1]["extra_body"] == {"provider_id": "pgvector"}


class TestKnowledgeBaseManagerRegisterKnowledgeBase:
    @pytest.mark.usefixtures("_mock_logger")
    def test_returns_none_when_no_llama_client(self):
        manager = KnowledgeBaseManager.__new__(KnowledgeBaseManager)
        manager._llama_client = None
        kb_dir = Path("/some/dir")
        result = manager.register_knowledge_base(kb_dir)
        assert result is None

    @pytest.mark.usefixtures("_mock_logger")
    def test_creates_vector_store_and_returns_id(self, tmp_path):
        kb_dir = tmp_path / "test-kb"
        kb_dir.mkdir()
        (kb_dir / "doc.txt").write_text("hello")

        manager = KnowledgeBaseManager(_make_mock_llama_client())
        manager._llama_client.vector_stores.create.return_value.id = "vs_new123"
        result = manager.register_knowledge_base(kb_dir)
        assert result == "vs_new123"

    @pytest.mark.usefixtures("_mock_logger")
    def test_returns_vector_store_id_even_when_no_txt_files(self, tmp_path):
        kb_dir = tmp_path / "empty-kb"
        kb_dir.mkdir()

        manager = KnowledgeBaseManager(_make_mock_llama_client())
        result = manager.register_knowledge_base(kb_dir)
        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.usefixtures("_mock_logger")
    def test_handles_openai_api_error(self, tmp_path):
        kb_dir = tmp_path / "fail-kb"
        kb_dir.mkdir()

        manager = KnowledgeBaseManager(_make_mock_llama_client())
        import openai
        manager._llama_client.vector_stores.create.side_effect = openai.APIError(
            request=MagicMock(), message="rate limited", body=None
        )
        result = manager.register_knowledge_base(kb_dir)
        assert result is None


class TestKnowledgeBaseManagerUploadFilesToVectorStore:
    @pytest.mark.usefixtures("_mock_logger")
    def test_returns_zero_when_no_llama_client(self, tmp_path):
        manager = KnowledgeBaseManager.__new__(KnowledgeBaseManager)
        manager._llama_client = None
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        result = manager._upload_files_to_vector_store(kb_dir, "vs_123")
        assert result == 0

    @pytest.mark.usefixtures("_mock_logger")
    def test_upload_one_txt_file(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "readme.txt").write_text("hello world")

        manager = KnowledgeBaseManager(_make_mock_llama_client())
        result = manager._upload_files_to_vector_store(kb_dir, "vs_123")
        assert result == 1
        manager._llama_client.files.create.assert_called_once()
        manager._llama_client.vector_stores.files.create.assert_called_once()

    @pytest.mark.usefixtures("_mock_logger")
    def test_upload_multiple_txt_files(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "a.txt").write_text("file a")
        (kb_dir / "b.txt").write_text("file b")
        (kb_dir / "c.md").write_text("not a txt")

        manager = KnowledgeBaseManager(_make_mock_llama_client())
        result = manager._upload_files_to_vector_store(kb_dir, "vs_123")
        assert result == 2

    @pytest.mark.usefixtures("_mock_logger")
    def test_skips_non_txt_files_via_rglob(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        (kb_dir / "a.txt").write_text("a")
        (kb_dir / "b.md").write_text("b")

        manager = KnowledgeBaseManager(_make_mock_llama_client())
        result = manager._upload_files_to_vector_store(kb_dir, "vs_123")
        assert result == 1

    @pytest.mark.usefixtures("_mock_logger")
    def test_continues_on_oserror_during_upload(self, tmp_path):
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        ok_file = kb_dir / "ok.txt"
        ok_file.write_text("ok")
        bad_file = kb_dir / "bad.txt"
        bad_file.write_text("bad")

        manager = KnowledgeBaseManager(_make_mock_llama_client())

        call_counts = [0]
        original_create = manager._llama_client.files.create

        def side_effect(*args, **kwargs):
            call_counts[0] += 1
            if call_counts[0] > 1:
                raise OSError("read error")
            resp = MagicMock()
            resp.id = f"file_{call_counts[0]}"
            return resp

        manager._llama_client.files.create.side_effect = side_effect
        result = manager._upload_files_to_vector_store(kb_dir, "vs_123")
        assert result == 1
