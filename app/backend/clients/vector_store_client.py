import logging
import os

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
        password = os.getenv("PG_PASSWORD", "password")
        db = os.getenv("PG_DB", "blueprint")

        connection_string = (
            f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
        )

        llama_stack_url = os.getenv(
            "LLAMA_STACK_URL", "http://llamastack:8321"
        ).rstrip("/")
        embed_model = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

        embeddings = OpenAIEmbeddings(
            api_key="not-required",
            base_url=f"{llama_stack_url}/v1/openai/v1",
            model=embed_model,
            tiktoken_enabled=False,
            check_embedding_ctx_length=False,
        )

        self.vector_store = PGVector(
            connection=connection_string,
            embeddings=embeddings,
            collection_name=_COLLECTION_NAME,
        )

        logger.info("VectorStoreClient connected to %s:%s/%s", host, port, db)

    def similarity_search(self, query: str, k: int = 3) -> list:
        """Return the top-k most similar documents for *query*."""
        return self.vector_store.similarity_search(query, k=k)

    def as_retriever(self, **kwargs):
        """Return a LangChain-compatible retriever."""
        return self.vector_store.as_retriever(**kwargs)

    def add_documents(self, documents: list, drop_old: bool = False) -> None:
        """Embed and store *documents* in the vector store."""
        if drop_old:
            try:
                self.vector_store.drop_tables()
                logger.info("Dropped existing tables for collection '%s'.", _COLLECTION_NAME)
            except Exception as exc:
                logger.warning("Could not drop tables: %s", exc)

        self.vector_store.create_tables_if_not_exists()
        self.vector_store.create_collection()
        logger.info("Schema and collection ready for '%s'.", _COLLECTION_NAME)

        self.vector_store.add_documents(documents)
        logger.info("Added %d documents to collection '%s'.", len(documents), _COLLECTION_NAME)
