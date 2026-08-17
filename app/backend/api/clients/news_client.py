"""Cached RSS client for world / business news headlines."""

from __future__ import annotations

import threading
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any, Optional

from logging_config import getLogger
import requests

logger = getLogger(__name__)

# Stable free RSS feeds (no API key). Override via Settings.news_feed_urls_raw
# (env var NEWS_FEED_URLS) if the cluster cannot reach these hosts
# (format: "Name|url;Name|url").
DEFAULT_FEEDS: tuple[tuple[str, str], ...] = (
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("The Guardian World", "https://www.theguardian.com/world/rss"),
)

_DEFAULT_USER_AGENT = (
    "ai-supply-chain-agent/1.0 (+https://github.com/rh-ai-quickstart/ai-supply-chain-agent; news-ticker)"
)


def feeds_from_env(raw: str | None = None) -> tuple[tuple[str, str], ...] | None:
    """Parse a ``Name|url;Name|url`` feed list (newlines also allowed)."""
    text = (raw or "").strip()
    if not text:
        return None
    feeds: list[tuple[str, str]] = []
    for part in text.replace("\n", ";").split(";"):
        entry = part.strip()
        if not entry:
            continue
        if "|" in entry:
            name, url = entry.split("|", 1)
            name, url = name.strip(), url.strip()
            if name and url:
                feeds.append((name, url))
        elif entry.startswith("http://") or entry.startswith("https://"):
            feeds.append(("News", entry))
    return tuple(feeds) if feeds else None


class NewsClient:
    """Fetches and merges RSS headlines with a short-lived in-memory cache."""

    CACHE_DURATION_SECONDS = 300

    def __init__(
        self,
        session: requests.Session | None = None,
        feeds: tuple[tuple[str, str], ...] | None = None,
        feed_urls_raw: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._session = session or requests.Session()
        if "User-Agent" not in self._session.headers:
            self._session.headers["User-Agent"] = user_agent or _DEFAULT_USER_AGENT
        self._feeds = feeds or feeds_from_env(feed_urls_raw) or DEFAULT_FEEDS
        self._lock = threading.Lock()
        self._cached_items: list[dict[str, Any]] | None = None
        self._last_fetch: float = 0.0

    def fetch_headlines(self, force: bool = False) -> list[dict[str, Any]]:
        """Return normalized headlines, or stale cache on failure, or ``[]``."""
        with self._lock:
            now = time.time()
            if (
                not force
                and self._cached_items is not None
                and (now - self._last_fetch) < self.CACHE_DURATION_SECONDS
            ):
                return list(self._cached_items)

        items = self._fetch_all_feeds()
        if items:
            with self._lock:
                self._cached_items = items
                self._last_fetch = time.time()
                logger.info("NewsClient: cached %s headlines", len(items))
            return list(items)

        with self._lock:
            return list(self._cached_items or [])

    def cache_age_seconds(self) -> Optional[float]:
        with self._lock:
            if self._cached_items is None or self._last_fetch <= 0:
                return None
            return time.time() - self._last_fetch

    def _fetch_all_feeds(self) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen_links: set[str] = set()
        for source, url in self._feeds:
            try:
                logger.info("NewsClient: requesting %s", url)
                response = self._session.get(url, timeout=8)
                if response.status_code != 200:
                    logger.warning(
                        "NewsClient: HTTP %s for %s",
                        response.status_code,
                        url,
                    )
                    continue
                for item in self._parse_rss(response.text, source=source):
                    link = item.get("link") or ""
                    key = link or f"{source}:{item.get('title', '')}"
                    if key in seen_links:
                        continue
                    seen_links.add(key)
                    merged.append(item)
            except (requests.RequestException, ET.ParseError, ValueError) as exc:
                logger.warning("NewsClient: error fetching %s: %s", url, exc)

        merged.sort(key=lambda row: row.get("published_at") or "", reverse=True)
        return merged

    @staticmethod
    def _parse_rss(xml_text: str, source: str) -> list[dict[str, Any]]:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            # Some feeds nest under a default namespace; try local-name fallback.
            channel = root.find(".//{*}channel")
        if channel is None:
            return []

        items: list[dict[str, Any]] = []
        for node in channel.findall("item") or channel.findall("{*}item"):
            title = _text(node, "title")
            if not title:
                continue
            link = _text(node, "link")
            summary = _text(node, "description")
            pub_raw = _text(node, "pubDate") or _text(node, "published")
            items.append(
                {
                    "title": title,
                    "link": link,
                    "source": source,
                    "published_at": _normalize_pub_date(pub_raw),
                    "summary": _strip_html(summary)[:400] if summary else "",
                }
            )
        return items


def _text(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    if child is None:
        child = node.find(f"{{*}}{tag}")
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _normalize_pub_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).isoformat()
    except (TypeError, ValueError, IndexError):
        return raw


def _strip_html(value: str) -> str:
    if not value:
        return ""
    # Lightweight strip for RSS descriptions that embed HTML.
    out: list[str] = []
    in_tag = False
    for ch in value:
        if ch == "<":
            in_tag = True
            continue
        if ch == ">":
            in_tag = False
            continue
        if not in_tag:
            out.append(ch)
    return "".join(out).strip()
