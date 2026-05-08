"""Create LlamaStack vector stores from uploaded files and record them in the demo catalog."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from clients.llama_stack_client import LlamaStackClient
from services.knowledge_bases_store import append_record, new_record_stub

logger = logging.getLogger(__name__)

_ALLOWED_SUFFIXES = (".txt", ".md", ".markdown", ".pdf")
_MAX_FILE_BYTES = 15 * 1024 * 1024
_MAX_FILES = 32


def _vector_store_slug(display_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", (display_name or "").strip())[:48].strip("-_.")
    if not slug:
        slug = "kb"
    return f"{slug}-{uuid.uuid4().hex[:8]}"


def ingest_uploaded_files(
    llama: LlamaStackClient,
    display_name: str,
    files: list[tuple[str, bytes]],
) -> dict[str, Any]:
    """Create a vector store, upload each allowed file, attach to the store, append catalog row.

    *files* is ``(original_filename, raw_bytes)`` pairs from multipart form uploads.
    """
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
    except Exception as exc:
        logger.exception("create_vector_store failed: %s", exc)
        return {"ok": False, "error": str(exc), "warnings": warnings}

    files_meta: list[dict[str, Any]] = []
    for filename, content in prepared:
        try:
            file_id = llama.upload_file_bytes(filename, content)
            llama.attach_file_to_vector_store(vector_store_id, file_id)
            files_meta.append({"filename": filename, "file_id": file_id, "bytes": len(content)})
        except Exception as exc:
            logger.warning("upload/attach failed for %s: %s", filename, exc)
            warnings.append(f"failed: {filename}: {exc}")

    if not files_meta:
        return {
            "ok": False,
            "error": "vector store was created but no files were ingested",
            "vector_store_id": vector_store_id,
            "warnings": warnings,
        }

    record = new_record_stub(
        name=display_name.strip(),
        vector_store_id=vector_store_id,
        files_meta=files_meta,
    )
    append_record(record)

    return {
        "ok": True,
        "knowledge_base": record,
        "warnings": warnings,
    }
