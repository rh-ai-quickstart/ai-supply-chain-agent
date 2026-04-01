import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


class LlamaStackVectorStoreClient:
    """Client for LlamaStack's OpenAI-compatible vector store and file APIs.

    Unlike VectorStoreClient (which writes to PGVector directly via LangChain),
    this client delegates storage entirely to LlamaStack.  It exposes three
    operations — create a vector store, upload a file, and attach the file to a
    store — which together let LlamaStack handle chunking, embedding, and
    persistence on the server side.
    """

    def __init__(self) -> None:
        base_url = os.getenv(
            "LLAMA_STACK_URL", "http://llamastack:8321"
        ).rstrip("/") + "/v1/openai/v1"

        self._client = OpenAI(
            api_key="not-required",
            base_url=base_url,
        )
        self._provider_id = os.getenv("VECTOR_STORE_PROVIDER", "pgvector")

        logger.info(
            "LlamaStackVectorStoreClient initialised — base_url=%s, provider=%s",
            base_url,
            self._provider_id,
        )

    def create_vector_store(self, name: str) -> str:
        """Create a named vector store backed by the configured provider.

        Returns the server-assigned vector store ID.
        """
        vector_store = self._client.vector_stores.create(
            name=name,
            extra_body={"provider_id": self._provider_id},
        )
        logger.info("Created vector store '%s' (id=%s)", name, vector_store.id)
        return vector_store.id

    def upload_file(self, file_path: str) -> str:
        """Upload a local file to LlamaStack and return the file ID."""
        with open(file_path, "rb") as fh:
            response = self._client.files.create(file=fh, purpose="assistants")
        logger.info("Uploaded file '%s' (id=%s)", file_path, response.id)
        return response.id

    def attach_file_to_store(self, vector_store_id: str, file_id: str) -> None:
        """Attach a previously uploaded file to a vector store.

        Once attached, LlamaStack chunks and embeds the file contents
        and indexes them in the vector store.
        """
        self._client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id,
        )
        logger.info(
            "Attached file %s to vector store %s", file_id, vector_store_id
        )
