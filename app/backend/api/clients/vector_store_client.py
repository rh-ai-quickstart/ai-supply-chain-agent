import logging

from clients.embedding_client import openai_embeddings_kwargs
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "supply_chain_risks"


class VectorStoreClient:
    """PGVector-backed vector store client."""

    def __init__(
        self,
        *,
        host: str = "pgvector",
        port: str = "5432",
        user: str = "postgres",
        password: str | None = None,
        database: str = "blueprint",
        llama_stack_url: str = "http://llamastack:8321",
        embed_model: str = "all-MiniLM-L6-v2",
        embed_base_url: str | None = None,
        embed_api_key: str | None = None,
    ) -> None:
        if not password:
            raise RuntimeError(
                "PG_PASSWORD environment variable is not set. "
                "The pgvector Helm chart creates a Secret; reference it via "
                "secretKeyRef in your Deployment env stanza."
            )
        db = database

        connection_string = (
            f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
        )

        llama_stack_url = llama_stack_url.rstrip("/")

        embed_kwargs = openai_embeddings_kwargs(
            llama_stack_url=llama_stack_url,
            embed_model=embed_model,
            embed_base_url=embed_base_url,
            embed_api_key=embed_api_key,
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

    def similarity_search(self, query: str, k: int = 3) -> list:
        """Return the top-k most similar documents for *query*."""
        return self.vector_store.similarity_search(query, k=k)
