"""Centralized runtime configuration for the API process.

Every environment variable the API reads lives here, mirroring the pattern
already used by ``ingestion/config.py`` (``IngestConfig.from_env()``). Clients
and services accept the specific values they need through their constructors
instead of calling ``os.getenv`` internally, which keeps them testable and
gives the composition root (``container.py``) a single source of truth.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes")


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """All tuneable parameters for the API process, sourced from env vars."""

    # Flask / web
    cors_origin: str | None = None
    flask_debug: bool = False

    # Llama Stack / OpenAI-compatible chat clients
    llama_stack_url: str = "http://llamastack:8321"
    llama_stack_model: str = field(
        default="llama-3-2-3b-instruct/meta-llama/Llama-3.2-3B-Instruct"
    )
    llama_stack_openai_model: str = ""
    llama_stack_timeout_seconds: int = 300
    openai_api_key: str | None = None
    vector_store_provider: str = "pgvector"

    # PGVector (langchain) direct access, used for the RAG fallback path
    pg_host: str = "pgvector"
    pg_port: str = "5432"
    pg_user: str = "postgres"
    pg_password: str | None = None
    pg_database: str = "blueprint"
    embed_model: str = "all-MiniLM-L6-v2"

    # General-simulation upstream service
    general_simulation_base_url: str = "http://localhost:8000"
    general_simulation_timeout_seconds: int = 120

    # News RSS
    news_feed_urls_raw: str = ""
    news_user_agent: str | None = None

    # Demo JSON catalogs (ephemeral; overridable for tests/tooling)
    knowledge_bases_store_path: str = "/tmp/supply-chain-knowledge-bases.json"

    # Build/version identifiers baked into the container image (see Containerfile
    # ARG/ENV + Makefile build-* targets); lets operators confirm a running pod
    # is actually serving the code they think it is.
    git_commit: str = "unknown"
    build_time: str = "unknown"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            cors_origin=os.getenv("CORS_ORIGIN") or None,
            flask_debug=_env_bool("FLASK_DEBUG", default=False),
            llama_stack_url=(os.getenv("LLAMA_STACK_URL") or "http://llamastack:8321"),
            llama_stack_model=os.getenv(
                "LLAMA_STACK_MODEL",
                "llama-3-2-3b-instruct/meta-llama/Llama-3.2-3B-Instruct",
            ),
            llama_stack_openai_model=os.getenv("LLAMA_STACK_OPENAI_MODEL", ""),
            llama_stack_timeout_seconds=_env_int("LLAMA_STACK_TIMEOUT_SECONDS", 300),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            vector_store_provider=os.getenv("VECTOR_STORE_PROVIDER", "pgvector"),
            pg_host=os.getenv("PG_HOST", "pgvector"),
            pg_port=os.getenv("PG_PORT", "5432"),
            pg_user=os.getenv("PG_USER", "postgres"),
            pg_password=os.environ.get("PG_PASSWORD"),
            pg_database=os.getenv("PG_DB", "blueprint"),
            embed_model=os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2"),
            general_simulation_base_url=os.getenv(
                "GENERAL_SIMULATION_BASE_URL", "http://localhost:8000"
            ),
            general_simulation_timeout_seconds=_env_int(
                "GENERAL_SIMULATION_TIMEOUT_SECONDS", 120
            ),
            news_feed_urls_raw=os.getenv("NEWS_FEED_URLS", ""),
            news_user_agent=os.getenv("NEWS_USER_AGENT") or None,
            knowledge_bases_store_path=os.getenv(
                "KNOWLEDGE_BASES_STORE_PATH", "/tmp/supply-chain-knowledge-bases.json"
            ),
            git_commit=os.getenv("GIT_COMMIT", "unknown"),
            build_time=os.getenv("BUILD_TIME", "unknown"),
        )
