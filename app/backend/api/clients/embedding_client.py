"""OpenAI-compatible embedding client settings (Llama Stack or direct MaaS)."""

from __future__ import annotations

import os


def openai_embeddings_kwargs(
    *,
    llama_stack_url: str,
    embed_model: str,
    embed_base_url: str | None = None,
    embed_api_key: str | None = None,
) -> dict[str, str]:
    """Build kwargs for ``langchain_openai.OpenAIEmbeddings``.

    When ``embed_base_url`` is set, embeddings bypass Llama Stack and call the
    remote OpenAI-compatible endpoint directly (required for MaaS embedding
    models — the llama-stack chart registers ``global.models`` only as ``llm``).
    """
    direct_base = (embed_base_url or os.getenv("EMBED_BASE_URL") or "").strip().rstrip("/")
    if direct_base:
        api_key = embed_api_key or os.getenv("EMBED_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "EMBED_API_KEY (or OPENAI_API_KEY) is required when EMBED_BASE_URL is set."
            )
        if not direct_base.endswith("/v1"):
            direct_base = f"{direct_base}/v1"
        return {"api_key": api_key, "base_url": direct_base, "model": embed_model}

    stack_url = (llama_stack_url or os.getenv("LLAMA_STACK_URL", "http://llamastack:8321")).rstrip(
        "/"
    )
    return {
        "api_key": "not-required",
        "base_url": f"{stack_url}/v1",
        "model": embed_model,
    }
