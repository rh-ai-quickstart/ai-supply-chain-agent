import os
from dataclasses import dataclass, field


@dataclass
class IngestConfig:
    """All tuneable parameters for the ingestion pipeline, sourced from env vars."""
    
    knowledge_base_dir: str = field(default="ingest/knowledge_base")
    chunk_size: int = field(default=1000)
    chunk_overlap: int = field(default=200)
    drop_old: bool = field(default=True)
    glob: str = field(default="**/*.txt")

    @classmethod
    def from_env(cls) -> "IngestConfig":
        return cls(
            knowledge_base_dir=os.getenv(
                "KNOWLEDGE_BASE_DIR", "ingest/knowledge_base"
            ),
            chunk_size=int(os.getenv("INGEST_CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("INGEST_CHUNK_OVERLAP", "200")),
            drop_old=os.getenv("INGEST_DROP_OLD", "true").lower() == "true",
            glob=os.getenv("INGEST_GLOB", "**/*.txt"),
        )
