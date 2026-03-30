import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an AI assistant for a supply chain command center. "
    "You help operators understand logistics data, demand forecasting, "
    "inventory levels, supplier risk, and shipping routes. "
    "Answer concisely and only about supply chain topics. "
    "If asked about unrelated topics, politely redirect to supply chain matters."
)


class LlamaStackClient:
    """OpenAI-compatible client pointed at a Llama Stack server."""

    def __init__(self, timeout_seconds: int = 30):
        self.base_url = os.getenv(
            "LLAMA_STACK_URL", "http://llamastack:8321"
        ).rstrip("/") + "/v1/openai/v1"
        self.model = os.getenv(
            "LLAMA_STACK_MODEL",
            "meta-llama/Llama-3.2-1B-Instruct",
        )
        self._timeout = timeout_seconds

        self._client = OpenAI(
            api_key="not-required",
            base_url=self.base_url,
        )

    def ask(self, user_input: str, context: str = "") -> str:
        """Send *user_input* to the LLM and return the text response.

        Args:
            user_input: The user's question or message.
            context:    Optional RAG context retrieved from the vector store.
                        When provided it is injected as a system message before
                        the user turn so the model can ground its answer.
        """
        if not self.base_url:
            return "Something went wrong. There is no endpoint configured."

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant context from the knowledge base:\n{context}",
                }
            )

        messages.append({"role": "user", "content": user_input})

        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                timeout=self._timeout,
            )
            return completion.choices[0].message.content or "Darn! Something went wrong."
        except Exception as exc:
            logger.error("Llama Stack request failed: %s", exc)
            return f"Darn! Something went wrong: {exc}"
