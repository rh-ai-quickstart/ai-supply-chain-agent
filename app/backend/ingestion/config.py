import os
from dataclasses import dataclass, field


@dataclass
class IngestConfig:
    """All tuneable parameters for the ingestion pipeline, sourced from env vars."""

    knowledge_base_dir: str = field(default="knowledge_base")
    glob: str = field(default="**/*.txt")
    file_status_timeout_seconds: int = field(default=300)
    file_status_poll_interval_seconds: int = field(default=5)

    @classmethod
    def from_env(cls) -> "IngestConfig":
        return cls(
            knowledge_base_dir=os.getenv(
                "KNOWLEDGE_BASE_DIR", "knowledge_base"
            ),
            glob=os.getenv("INGEST_GLOB", "**/*.txt"),
            file_status_timeout_seconds=int(
                os.getenv("INGEST_FILE_STATUS_TIMEOUT_SECONDS", "300")
            ),
            file_status_poll_interval_seconds=int(
                os.getenv("INGEST_FILE_STATUS_POLL_INTERVAL_SECONDS", "5")
            ),
        )
