"""Off-topic chat guardrail (extracted from ``ChatService`` for SRP).

Uses word-boundary matching so a keyword like ``"food"`` only blocks whole
words, not substrings inside unrelated terms such as ``"seafood logistics"``
(``suggestions.md`` debt M5 — the previous ``keyword in lowered`` check also
let ``"pizza"`` match ``"pizzazz"``).
"""

from __future__ import annotations

import re

GUARDRAIL_KEYWORDS: tuple[str, ...] = (
    "restaurant",
    "food",
    "weather",
    "sports",
    "movie",
    "pizza",
    "burger",
    "joke",
    "politics",
)

GUARDRAIL_RESPONSE = (
    "I am restricted to supply chain topics only. "
    "Please ask about logistics, demand, routing, or risk."
)

_KEYWORD_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE) for keyword in GUARDRAIL_KEYWORDS
)


class GuardrailPolicy:
    """Decides whether a chat turn is off-topic for the supply-chain assistant."""

    RESPONSE = GUARDRAIL_RESPONSE

    def is_blocked(self, text: str) -> bool:
        value = text or ""
        return any(pattern.search(value) for pattern in _KEYWORD_PATTERNS)

    def blocked_response(self) -> dict[str, object]:
        return {"answer": self.RESPONSE, "completion": None}
