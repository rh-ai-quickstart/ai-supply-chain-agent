import logging
import uuid
from pathlib import Path

from clients.llamastack_vector_store_client import LlamaStackVectorStoreClient
from config import IngestConfig

logger = logging.getLogger(__name__)


class LlamaStackIngestionService:
    """Server-side ingestion that delegates chunking, embedding, and storage to LlamaStack.

    The existing IngestionService performs all these steps client-side with
    LangChain and writes directly to PGVector.  This service instead uploads
    the raw knowledge-base files to LlamaStack's OpenAI-compatible
    ``vector_stores`` / ``files`` API and lets the server handle the full
    pipeline, which keeps the client thin and leverages whatever chunking
    and embedding strategy LlamaStack is configured with.
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

        store_name = f"supply-chain-kb-{uuid.uuid4().hex[:8]}"
        vector_store_id = self._client.create_vector_store(store_name)

        uploaded = 0
        for file_path in files:
            try:
                file_id = self._client.upload_file(str(file_path))
                self._client.attach_file_to_store(vector_store_id, file_id)
                uploaded += 1
            except Exception as exc:
                logger.error("Failed to ingest '%s': %s", file_path, exc)

        logger.info(
            "Pipeline finished — %d/%d file(s) ingested into store '%s' (%s)",
            uploaded,
            len(files),
            store_name,
            vector_store_id,
        )
        return uploaded
