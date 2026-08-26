import logging
import os

from clients.embedding_client import openai_embeddings_kwargs
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "supply_chain_risks"


class VectorStoreClient:
    """PGVector-backed vector store client."""

    def __init__(self) -> None:
        host = os.getenv("PG_HOST", "pgvector")
        port = os.getenv("PG_PORT", "5432")
        user = os.getenv("PG_USER", "postgres")
        pg_password = os.environ.get("PG_PASSWORD")
        if not pg_password:
            raise RuntimeError(
                "PG_PASSWORD environment variable is not set. "
                "The pgvector Helm chart creates a Secret; reference it via "
                "secretKeyRef in your Deployment env stanza."
            )
        password = pg_password
        db = os.getenv("PG_DB", "blueprint")

        connection_string = (
            f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
        )

        llama_stack_url = os.getenv(
            "LLAMA_STACK_URL", "http://llamastack:8321"
        ).rstrip("/")
        embed_model = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

        embed_kwargs = openai_embeddings_kwargs(
            llama_stack_url=llama_stack_url,
            embed_model=embed_model,
        )
        embeddings = OpenAIEmbeddings(
            tiktoken_enabled=False,
            check_embedding_ctx_length=False,
            **embed_kwargs,
        )

        self.vector_store = PGVector(
            connection=connection_string,
            embeddings=embeddings,
            collection_name=_COLLECTION_NAME,
        )

        logger.info("VectorStoreClient connected to %s:%s/%s", host, port, db)

    def add_documents(self, documents: list, drop_old: bool = False) -> None:
        """Embed and store *documents* in the vector store."""
        if drop_old:
            try:
                self.vector_store.drop_tables()
                logger.info("Dropped existing tables for collection '%s'.", _COLLECTION_NAME)
            # Broad catch: best-effort cleanup; dropping tables is optional, continue on failure.
            except Exception as exc:
                    logger.warning("Could not drop tables: %s", exc)

        self.vector_store.create_tables_if_not_exists()
        self.vector_store.create_collection()
        logger.info("Schema and collection ready for '%s'.", _COLLECTION_NAME)

        self.vector_store.add_documents(documents)
        logger.info("Added %d documents to collection '%s'.", len(documents), _COLLECTION_NAME)
