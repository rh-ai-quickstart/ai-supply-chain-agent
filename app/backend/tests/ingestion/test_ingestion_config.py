"""``IngestConfig`` environment parsing."""

from config import IngestConfig


def test_from_env_default():
    cfg = IngestConfig.from_env()
    assert cfg.knowledge_base_dir == "knowledge_base"
    assert cfg.glob == "**/*.txt"


def test_from_env_overrides(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BASE_DIR", "/data/kb")
    monkeypatch.setenv("INGEST_GLOB", "*.txt")
    cfg = IngestConfig.from_env()
    assert cfg.knowledge_base_dir == "/data/kb"
    assert cfg.glob == "*.txt"
