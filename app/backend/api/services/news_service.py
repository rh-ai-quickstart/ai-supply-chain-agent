"""Business logic for supply-chain news headlines."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from clients.news_client import NewsClient

_SUPPLY_CHAIN_RE = re.compile(
    r"\b("
    r"supply\s*chain|logistics|shipping|freight|cargo|port|ports|"
    r"vessel|vessels|container|containers|warehouse|warehouses|"
    r"rail|truck|trucking|airline|airspace|airport|flight|"
    r"suez|panama|canal|strike|blockade|sanctions|tariff|tariffs|"
    r"oil|energy|commodity|commodities|semiconductor|chip|"
    r"factory|manufactur|export|import|trade\s+war|geopolitic|"
    r"hurricane|typhoon|flood|earthquake|disruption|delay"
    r")\b",
    re.IGNORECASE,
)


class NewsService:
    def __init__(self, client: NewsClient | None = None) -> None:
        self._client = client or NewsClient()

    def get_headlines(self, limit: int = 30) -> dict[str, Any]:
        """Return ticker/API payload with recent headlines."""
        capped = max(1, min(int(limit or 30), 50))
        items = self._client.fetch_headlines()[:capped]
        return {
            "items": items,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "cache_age_seconds": self._client.cache_age_seconds(),
        }

    def format_for_chat(self, headlines: Optional[list[dict[str, Any]]] = None, limit: int = 12) -> str:
        """Build a chat-facing summary emphasizing supply-chain relevance."""
        items = headlines if headlines is not None else self._client.fetch_headlines()
        if not items:
            return (
                "I could not retrieve recent news headlines right now. "
                "Please try again in a few minutes."
            )

        capped = items[: max(1, min(int(limit or 12), 25))]
        relevant = [item for item in capped if self._is_supply_chain_relevant(item)]
        focus = relevant or capped[:8]

        lines = [
            "Here are recent headlines that may affect the supply chain:",
            "",
        ]
        for item in focus:
            source = item.get("source") or "News"
            title = item.get("title") or "Untitled"
            link = item.get("link") or ""
            flag = " (supply-chain relevant)" if item in relevant else ""
            if link:
                lines.append(f"- **{source}:** [{title}]({link}){flag}")
            else:
                lines.append(f"- **{source}:** {title}{flag}")

        if relevant:
            lines.extend(
                [
                    "",
                    f"{len(relevant)} of the latest {len(capped)} headlines look "
                    "especially relevant to logistics, trade, or disruption risk.",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "None of the latest headlines clearly match supply-chain keywords, "
                    "but world and business events above can still ripple into logistics.",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def _is_supply_chain_relevant(item: dict[str, Any]) -> bool:
        blob = " ".join(
            [
                str(item.get("title") or ""),
                str(item.get("summary") or ""),
            ]
        )
        return bool(_SUPPLY_CHAIN_RE.search(blob))
