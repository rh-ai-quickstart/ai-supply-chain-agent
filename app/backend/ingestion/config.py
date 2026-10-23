import os
from dataclasses import dataclass, field


@dataclass
class IngestConfig:
    """All tuneable parameters for the ingestion pipeline, sourced from env vars."""

    knowledge_base_dir: str = field(default="knowledge_base")
    glob: str = field(default="**/*.txt")

    @classmethod
    def from_env(cls) -> "IngestConfig":
        return cls(
            knowledge_base_dir=os.getenv(
                "KNOWLEDGE_BASE_DIR", "knowledge_base"
            ),
            glob=os.getenv("INGEST_GLOB", "**/*.txt"),
        )
