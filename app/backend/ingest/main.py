import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    from clients.vector_store_client import VectorStoreClient
    from ingest.config import IngestConfig
    from ingest.loaders.document_loader import DocumentLoader
    from ingest.services.ingestion_service import IngestionService

    config = IngestConfig.from_env()

    logger.info("=== Knowledge Base Ingestion ===")
    logger.info("  Source dir   : %s", config.knowledge_base_dir)
    logger.info("  File glob    : %s", config.glob)
    logger.info("  Chunk size   : %d", config.chunk_size)
    logger.info("  Chunk overlap: %d", config.chunk_overlap)
    logger.info("  Drop old     : %s", config.drop_old)

    try:
        vector_store_client = VectorStoreClient()
        document_loader = DocumentLoader(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            glob=config.glob,
        )
        service = IngestionService(vector_store_client, document_loader)
        count = service.run(config)
        logger.info("=== Done: %d chunk(s) stored ===", count)
    except FileNotFoundError as exc:
        logger.error("Source directory missing — %s", exc)
        sys.exit(1)
    except ValueError as exc:
        logger.error("No documents to ingest — %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected error during ingestion: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
