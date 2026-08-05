import logging
import uuid
from pathlib import Path

import openai
from clients.llamastack_vector_store_client import LlamaStackVectorStoreClient
from config import IngestConfig

logger = logging.getLogger(__name__)


def _vector_store_name_for_kb(kb_dir: Path) -> str:
    """Build a LlamaStack vector store name for a whole knowledge base.

    One store is created per knowledge base directory (not per file).  The name
    is derived from the directory basename and made unique per run with a short
    uuid so repeated runs do not collide.
    """
    base = kb_dir.name or "knowledge_base"
    return f"{base}-{uuid.uuid4().hex[:8]}"


class LlamaStackIngestionService:
    """Server-side ingestion that delegates chunking, embedding, and storage to LlamaStack.

    The existing IngestionService performs all these steps client-side with
    LangChain and writes directly to PGVector.  This service instead uploads
    the raw knowledge-base files to LlamaStack's OpenAI-compatible
    ``vector_stores`` / ``files`` API and lets the server handle the full
    pipeline, which keeps the client thin and leverages whatever chunking
    and embedding strategy LlamaStack is configured with.

    Unlike a naive one-vector-store-per-file approach, this service creates a
    SINGLE vector store for the whole knowledge base and uploads every matched
    file into it.  Per-file metadata (the source filename) is carried on each
    uploaded File (best-effort via the SDK's ``extra_body``), so documents can
    still be filtered/attributed to their source file.  If LlamaStack does not
    persist that metadata, the source filename remains attached to the File
    server-side and can be used for attribution.
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

        store_name = _vector_store_name_for_kb(kb_dir)
        try:
            vector_store_id = self._client.create_vector_store(store_name)
        except (openai.APIError, OSError) as exc:
            logger.error(
                "Failed to create vector store '%s' for KB '%s': %s",
                store_name,
                kb_dir,
                exc,
            )
            return 0

        uploaded = 0
        for file_path in sorted(files):
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

        logger.info(
            "Pipeline finished — %d/%d file(s) ingested into one vector store per KB ('%s').",
            uploaded,
            len(files),
            store_name,
        )
        return uploaded
