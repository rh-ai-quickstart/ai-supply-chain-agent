"""``IngestConfig`` environment parsing."""

from config import IngestConfig, IngestionStrategy


def test_from_env_default():
    cfg = IngestConfig.from_env()
    assert isinstance(cfg.strategy, IngestionStrategy)


def test_from_env_unknown_strategy_defaults_to_langchain(monkeypatch):
    monkeypatch.setenv("INGEST_STRATEGY", "not-a-real-strategy")
    cfg = IngestConfig.from_env()
    assert cfg.strategy == IngestionStrategy.LANGCHAIN


def test_from_env_llamastack(monkeypatch):
    monkeypatch.setenv("INGEST_STRATEGY", "llamastack")
    monkeypatch.setenv("INGEST_CHUNK_SIZE", "512")
    monkeypatch.setenv("INGEST_DROP_OLD", "false")
    cfg = IngestConfig.from_env()
    assert cfg.strategy == IngestionStrategy.LLAMASTACK
    assert cfg.chunk_size == 512
    assert cfg.drop_old is False
