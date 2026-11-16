import logging
import os
import time

from openai import OpenAI

logger = logging.getLogger(__name__)


class LlamaStackVectorStoreClient:
    """Client for LlamaStack's OpenAI-compatible vector store and file APIs.

    Delegates chunking, embedding, and storage to LlamaStack via the vector
    stores / files API.
    """

    def __init__(self) -> None:
        base_url = os.getenv(
            "LLAMA_STACK_URL", "http://llamastack:8321"
        ).rstrip("/") + "/v1"

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

    def upload_file(self, file_path: str, **metadata) -> str:
        """Upload a local file to LlamaStack and return the file ID.

        Optional keyword arguments are carried as per-file attributes on the
        uploaded File object so documents belonging to the same vector store
        can still be filtered/attributed to their source file.

        Note: the installed openai SDK's ``files.create`` does not expose a
        dedicated ``attributes``/``metadata`` parameter.  Metadata is therefore
        sent best-effort via ``extra_body`` (the SDK's documented catch-all for
        additional JSON request properties).  Whether LlamaStack persists it
        depends on the server; see the service docstring for the fallback
        attribution strategy.
        """
        with open(file_path, "rb") as fh:
            if metadata:
                response = self._client.files.create(
                    file=fh,
                    purpose="assistants",
                    extra_body={"attributes": metadata},
                )
            else:
                response = self._client.files.create(
                    file=fh, purpose="assistants"
                )
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

    def wait_for_file_processing(
        self,
        vector_store_id: str,
        file_id: str,
        *,
        timeout_seconds: int = 300,
        poll_interval_seconds: int = 5,
    ):
        """Wait for LlamaStack to finish indexing an attached file.

        The attach endpoint may return HTTP 200 even if asynchronous parsing or
        embedding later fails, so ingestion must inspect the file status.
        """
        deadline = time.monotonic() + max(1, timeout_seconds)
        poll_interval = max(1, poll_interval_seconds)

        while True:
            file_status = self._client.vector_stores.files.retrieve(
                vector_store_id=vector_store_id,
                file_id=file_id,
            )
            status = getattr(file_status, "status", "unknown")

            if status == "completed":
                logger.info(
                    "File indexing completed file=%s store=%s usage_bytes=%s",
                    file_id,
                    vector_store_id,
                    getattr(file_status, "usage_bytes", None),
                )
                return file_status

            if status in {"failed", "cancelled"}:
                last_error = getattr(file_status, "last_error", None)
                if isinstance(last_error, dict):
                    error_detail = last_error.get("message") or last_error.get("code")
                else:
                    error_detail = getattr(last_error, "message", None)
                detail = f": {error_detail}" if error_detail else ""
                raise RuntimeError(
                    f"LlamaStack file indexing {status} for file {file_id} "
                    f"in vector store {vector_store_id}{detail}"
                )

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Timed out after {timeout_seconds}s waiting for LlamaStack "
                    f"to index file {file_id} in vector store {vector_store_id}; "
                    f"last status={status!r}"
                )

            logger.info(
                "Waiting for LlamaStack file indexing file=%s store=%s status=%s",
                file_id,
                vector_store_id,
                status,
            )
            time.sleep(min(poll_interval, remaining))

    def delete_vector_store(self, vector_store_id: str) -> None:
        """Delete a vector store by id. Used for cleanup on partial ingestion failure."""
        self._client.vector_stores.delete(vector_store_id)
        logger.info("Deleted vector store %s", vector_store_id)
