"""Create LlamaStack vector stores from uploaded files and record them in the demo catalog."""

from __future__ import annotations

import logging
import re
from typing import Any

import openai
from clients.llama_stack_client import LlamaStackClient
from repositories.knowledge_base_repository import KnowledgeBaseRepository

logger = logging.getLogger(__name__)

_ALLOWED_SUFFIXES = (".txt", ".md", ".markdown", ".pdf")
_MAX_FILE_BYTES = 15 * 1024 * 1024
_MAX_FILES = 32

# LlamaStack vector store names have a 48-character limit.
_MAX_VECTOR_STORE_NAME_LENGTH = 48


def _vector_store_slug(display_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", (display_name or "").strip())[:_MAX_VECTOR_STORE_NAME_LENGTH].strip("-_.")
    return slug


def ingest_uploaded_files(
    llama: LlamaStackClient,
    display_name: str,
    files: list[tuple[str, bytes]],
    *,
    repository: KnowledgeBaseRepository | None = None,
) -> dict[str, Any]:
    """Create a vector store, upload each allowed file, attach to the store, append catalog row.

    *files* is ``(original_filename, raw_bytes)`` pairs from multipart form uploads.
    """
    repo = repository or KnowledgeBaseRepository()
    warnings: list[str] = []
    if not (display_name or "").strip():
        return {"ok": False, "error": "name is required"}

    if not files:
        return {"ok": False, "error": "at least one file is required"}

    if len(files) > _MAX_FILES:
        return {"ok": False, "error": f"at most {_MAX_FILES} files per request"}

    prepared: list[tuple[str, bytes]] = []
    for orig_name, data in files:
        name = (orig_name or "unnamed").rsplit("/")[-1].rsplit("\\")[-1]
        lower = name.lower()
        if not any(lower.endswith(s) for s in _ALLOWED_SUFFIXES):
            warnings.append(f"skipped (unsupported type): {name}")
            continue
        if len(data) > _MAX_FILE_BYTES:
            warnings.append(f"skipped (too large, max {_MAX_FILE_BYTES} bytes): {name}")
            continue
        if not data:
            warnings.append(f"skipped (empty): {name}")
            continue
        prepared.append((name, data))

    if not prepared:
        return {"ok": False, "error": "no acceptable files after validation", "warnings": warnings}

    store_label = _vector_store_slug(display_name)
    try:
        vector_store_id = llama.create_vector_store(store_label)
    except (openai.APIError, RuntimeError) as exc:
        logger.exception("create_vector_store failed: %s", exc)
        return {"ok": False, "error": str(exc), "warnings": warnings}

    files_meta: list[dict[str, Any]] = []
    try:
        for filename, content in prepared:
            file_id = llama.upload_file_bytes(filename, content)
            llama.attach_file_to_vector_store(vector_store_id, file_id)
            files_meta.append({"filename": filename, "file_id": file_id, "bytes": len(content)})
    except Exception as exc:
        logger.exception("ingestion failed for store=%s; cleaning up", vector_store_id)
        llama.delete_vector_store(vector_store_id)
        return {
            "ok": False,
            "error": str(exc),
            "vector_store_id": vector_store_id,
        }

    if not files_meta:
        logger.info("no files ingested for store=%s; cleaning up", vector_store_id)
        llama.delete_vector_store(vector_store_id)
        return {
            "ok": False,
            "error": "vector store was created but no files were ingested",
            "vector_store_id": vector_store_id,
            "warnings": warnings,
        }

    record = repo.append_upload(
        name=display_name.strip(),
        vector_store_id=vector_store_id,
        files_meta=files_meta,
    )

    return {
        "ok": True,
        "knowledge_base": record,
        "warnings": warnings,
    }
