import logging
import uuid
from pathlib import Path

import openai
from clients.llamastack_vector_store_client import LlamaStackVectorStoreClient
from config import IngestConfig

logger = logging.getLogger(__name__)


def _vector_store_name_for_file(file_path: Path) -> str:
    """Build a LlamaStack vector store name for a single knowledge-base file.

    One store is created per source document so simulation scenarios can select
    the matching store by filename keywords. A short uuid suffix keeps repeated
    ingest runs from colliding on the same name.
    """
    base = file_path.stem or "knowledge_base"
    return f"{base}-{uuid.uuid4().hex[:8]}"


class LlamaStackIngestionService:
    """Server-side ingestion that delegates chunking, embedding, and storage to LlamaStack.

    The existing IngestionService performs all these steps client-side with
    LangChain and writes directly to PGVector.  This service instead uploads
    the raw knowledge-base files to LlamaStack's OpenAI-compatible
    ``vector_stores`` / ``files`` API and lets the server handle the full
    pipeline, which keeps the client thin and leverages whatever chunking
    and embedding strategy LlamaStack is configured with.

    Creates one vector store per matched file. Store names are derived from the
    source filename stem so the simulation UI can map scenarios (UK airspace,
    Port Strike LA, Suez blockage) to the corresponding knowledge base.
    """

    def __init__(
        self,
        vector_store_client: LlamaStackVectorStoreClient,
    ) -> None:
        self._client = vector_store_client

    def run(self, config: IngestConfig) -> int:
        """Execute the ingestion pipeline.

        Returns the number of files successfully ingested.
        """
        kb_dir = Path(config.knowledge_base_dir)
        if not kb_dir.exists():
            raise FileNotFoundError(
                f"Knowledge base directory not found: {kb_dir!r}"
            )

        files = [f for f in kb_dir.rglob(config.glob) if f.is_file()]

        if not files:
            raise ValueError(
                f"No files matched glob '{config.glob}' in '{kb_dir}'. "
                "Add files to the knowledge_base directory and retry."
            )

        logger.info("Found %d file(s) in '%s'", len(files), kb_dir)

        uploaded = 0
        for file_path in sorted(files):
            store_name = _vector_store_name_for_file(file_path)
            try:
                vector_store_id = self._client.create_vector_store(store_name)
            except (openai.APIError, OSError) as exc:
                logger.error(
                    "Failed to create vector store '%s' for '%s': %s",
                    store_name,
                    file_path,
                    exc,
                )
                continue

            try:
                file_id = self._client.upload_file(
                    str(file_path), source_filename=file_path.name
                )
                self._client.attach_file_to_store(vector_store_id, file_id)
                uploaded += 1
                logger.info(
                    "Ingested '%s' into vector store '%s' (%s)",
                    file_path.name,
                    store_name,
                    vector_store_id,
                )
            except (openai.APIError, OSError) as exc:
                logger.error(
                    "Failed to ingest '%s' (store name '%s'): %s",
                    file_path,
                    store_name,
                    exc,
                )
                try:
                    self._client.delete_vector_store(vector_store_id)
                except (openai.APIError, OSError, AttributeError):
                    logger.warning(
                        "Could not clean up vector store '%s' after failed ingest",
                        vector_store_id,
                    )

        logger.info(
            "Pipeline finished — %d/%d file(s) ingested (one vector store per file).",
            uploaded,
            len(files),
        )
        return uploaded
