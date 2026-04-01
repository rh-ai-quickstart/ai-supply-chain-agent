import os
from dataclasses import dataclass, field
from enum import Enum


class IngestionStrategy(Enum):
    """Which backend performs chunking, embedding, and storage."""

    LANGCHAIN = "langchain"
    LLAMASTACK = "llamastack"


@dataclass
class IngestConfig:
    """All tuneable parameters for the ingestion pipeline, sourced from env vars."""

    strategy: IngestionStrategy = field(default=IngestionStrategy.LANGCHAIN)
    knowledge_base_dir: str = field(default="knowledge_base")
    glob: str = field(default="**/*.txt")

    # --- langchain strategy only ---
    chunk_size: int = field(default=1000)
    chunk_overlap: int = field(default=200)
    drop_old: bool = field(default=True)

    @classmethod
    def from_env(cls) -> "IngestConfig":
        raw_strategy = os.getenv("INGEST_STRATEGY", "langchain").lower()
        try:
            strategy = IngestionStrategy(raw_strategy)
        except ValueError:
            strategy = IngestionStrategy.LANGCHAIN

        return cls(
            strategy=strategy,
            knowledge_base_dir=os.getenv(
                "KNOWLEDGE_BASE_DIR", "knowledge_base"
            ),
            glob=os.getenv("INGEST_GLOB", "**/*.txt"),
            chunk_size=int(os.getenv("INGEST_CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("INGEST_CHUNK_OVERLAP", "200")),
            drop_old=os.getenv("INGEST_DROP_OLD", "true").lower() == "true",
        )
