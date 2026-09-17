from logging_config import setup_logging, getLogger

setup_logging()
logger = getLogger(__name__)


def main() -> None:
    from clients.llamastack_vector_store_client import LlamaStackVectorStoreClient
    from config import IngestConfig
    from services.llamastack_ingestion_service import LlamaStackIngestionService

    config = IngestConfig.from_env()

    logger.info("=== Knowledge Base Ingestion ===")
    logger.info("  Source dir   : %s", config.knowledge_base_dir)
    logger.info("  File glob    : %s", config.glob)

    try:
        client = LlamaStackVectorStoreClient()
        service = LlamaStackIngestionService(client)
        count = service.run(config)
        logger.info("=== Done: %d item(s) ingested ===", count)
    except FileNotFoundError as exc:
        logger.error("Source directory missing — %s", exc)
        raise
    except ValueError as exc:
        logger.error("No documents to ingest — %s", exc)
        raise
    except Exception as exc:
        logger.exception("Unexpected error during ingestion: %s", exc)
        raise


if __name__ == "__main__":
    main()
