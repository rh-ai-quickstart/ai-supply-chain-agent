import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _build_langchain_service():
    from clients.vector_store_client import VectorStoreClient
    from config import IngestConfig
    from loaders.document_loader import DocumentLoader
    from services.ingestion_service import IngestionService

    config = IngestConfig.from_env()
    vector_store_client = VectorStoreClient()
    document_loader = DocumentLoader(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        glob=config.glob,
    )
    return IngestionService(vector_store_client, document_loader), config


def _build_llamastack_service():
    from clients.llamastack_vector_store_client import LlamaStackVectorStoreClient
    from config import IngestConfig
    from services.llamastack_ingestion_service import LlamaStackIngestionService

    config = IngestConfig.from_env()
    client = LlamaStackVectorStoreClient()
    return LlamaStackIngestionService(client), config


def main() -> None:
    from config import IngestConfig, IngestionStrategy

    config = IngestConfig.from_env()

    logger.info("=== Knowledge Base Ingestion ===")
    logger.info("  Strategy     : %s", config.strategy.value)
    logger.info("  Source dir   : %s", config.knowledge_base_dir)
    logger.info("  File glob    : %s", config.glob)
    if config.strategy == IngestionStrategy.LANGCHAIN:
        logger.info("  Chunk size   : %d", config.chunk_size)
        logger.info("  Chunk overlap: %d", config.chunk_overlap)
        logger.info("  Drop old     : %s", config.drop_old)

    try:
        if config.strategy == IngestionStrategy.LLAMASTACK:
            service, config = _build_llamastack_service()
        else:
            service, config = _build_langchain_service()

        count = service.run(config)
        logger.info("=== Done: %d item(s) ingested ===", count)
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
