import logging

from clients.vector_store_client import VectorStoreClient
from config import IngestConfig
from loaders.document_loader import DocumentLoader

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates the end-to-end knowledge-base ingestion pipeline."""

    def __init__(
        self,
        vector_store_client: VectorStoreClient,
        document_loader: DocumentLoader,
    ) -> None:
        self._vector_store = vector_store_client
        self._loader = document_loader

    def run(self, config: IngestConfig) -> int:
        logger.info("Pipeline started — source: '%s'", config.knowledge_base_dir)

        chunks = self._loader.load_and_split(config.knowledge_base_dir)

        logger.info(
            "Storing %d chunk(s) — drop_old=%s", len(chunks), config.drop_old
        )
        self._vector_store.add_documents(chunks, drop_old=config.drop_old)

        logger.info("Pipeline finished — %d chunk(s) ingested.", len(chunks))
        return len(chunks)
