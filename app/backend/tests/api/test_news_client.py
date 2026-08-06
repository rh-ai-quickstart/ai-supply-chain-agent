"""``NewsClient`` RSS parsing and cache behavior with a mocked session."""

from unittest.mock import MagicMock

import requests
from clients.news_client import NewsClient

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Port strike disrupts shipping</title>
      <link>https://example.com/1</link>
      <description>Dockworkers walk out at a major port.</description>
      <pubDate>Mon, 05 Aug 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Local sports final</title>
      <link>https://example.com/2</link>
      <description>Team wins championship.</description>
      <pubDate>Mon, 05 Aug 2026 11:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def _ok_response(text: str = SAMPLE_RSS) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.text = text
    return response


def test_fetch_headlines_parses_and_caches():
    session = MagicMock()
    session.headers = {}
    session.get.return_value = _ok_response()
    client = NewsClient(
        session=session,
        feeds=(("Test", "https://example.com/rss"),),
    )
    first = client.fetch_headlines()
    second = client.fetch_headlines()
    assert len(first) == 2
    assert first[0]["title"] == "Port strike disrupts shipping"
    assert first[0]["source"] == "Test"
    assert first[0]["link"] == "https://example.com/1"
    assert first is not second
    assert first == second
    assert session.get.call_count == 1


def test_fetch_headlines_returns_stale_cache_on_error():
    session = MagicMock()
    session.headers = {}
    ok = _ok_response()
    bad = MagicMock()
    bad.status_code = 503
    session.get.side_effect = [ok, bad]
    client = NewsClient(
        session=session,
        feeds=(("Test", "https://example.com/rss"),),
    )
    client.CACHE_DURATION_SECONDS = 0
    first = client.fetch_headlines()
    second = client.fetch_headlines()
    assert len(first) == 2
    assert second == first


def test_fetch_headlines_empty_on_network_error_without_cache():
    session = MagicMock()
    session.headers = {}
    session.get.side_effect = requests.RequestException("down")
    client = NewsClient(
        session=session,
        feeds=(("Test", "https://example.com/rss"),),
    )
    assert client.fetch_headlines() == []


def test_feeds_from_env_parses_name_url_pairs():
    from clients.news_client import feeds_from_env

    feeds = feeds_from_env(
        "BBC|https://example.com/a;Biz|https://example.com/b"
    )
    assert feeds == (
        ("BBC", "https://example.com/a"),
        ("Biz", "https://example.com/b"),
    )


def test_news_client_sets_user_agent():
    session = MagicMock()
    session.headers = {}
    session.get.return_value = _ok_response()
    NewsClient(session=session, feeds=(("Test", "https://example.com/rss"),))
    assert "User-Agent" in session.headers
