"""UI-uploaded knowledge-base catalog routes."""

from __future__ import annotations

from container import Container
from flask import Blueprint, jsonify, request
from services.knowledge_base_ingest_service import ingest_uploaded_files


def create_blueprint(container: Container) -> Blueprint:
    bp = Blueprint("knowledge_bases", __name__)

    @bp.route("/api/v1/knowledge-bases", methods=["GET"])
    def get_knowledge_bases():
        """UI-upload catalog only. Merge with ``GET /api/v1/vector_stores`` in the client (same source as chat)."""
        return jsonify({"knowledge_bases": container.knowledge_base_repository.load_all()})

    @bp.route("/api/v1/knowledge-bases", methods=["POST"])
    def post_knowledge_bases():
        """Multipart: ``name`` (text) + ``files`` (one or more uploads) → LlamaStack vector store."""
        name = (request.form.get("name") or "").strip()
        uploads = request.files.getlist("files")
        pairs: list[tuple[str, bytes]] = []
        for storage in uploads:
            if storage and storage.filename:
                pairs.append((storage.filename, storage.read()))
        result = ingest_uploaded_files(
            container.chat_service.llama_stack_client,
            name,
            pairs,
            repository=container.knowledge_base_repository,
        )
        if not result.get("ok"):
            return jsonify(result), 400
        return jsonify(result), 201

    return bp
