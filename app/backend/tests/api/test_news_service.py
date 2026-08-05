"""``NewsService`` headline formatting."""

from unittest.mock import MagicMock

from services.news_service import NewsService


def test_get_headlines_caps_limit():
    client = MagicMock()
    client.fetch_headlines.return_value = [
        {"title": f"Story {i}", "link": f"https://ex/{i}", "source": "Test"}
        for i in range(40)
    ]
    client.cache_age_seconds.return_value = 1.5
    service = NewsService(client=client)
    out = service.get_headlines(limit=5)
    assert len(out["items"]) == 5
    assert "fetched_at" in out
    assert out["cache_age_seconds"] == 1.5


def test_format_for_chat_flags_supply_chain_relevant():
    client = MagicMock()
    service = NewsService(client=client)
    text = service.format_for_chat(
        [
            {
                "title": "Port strike hits Los Angeles",
                "link": "https://example.com/port",
                "source": "BBC",
                "summary": "Dockworkers walk out",
            },
            {
                "title": "Celebrity awards night",
                "link": "https://example.com/awards",
                "source": "BBC",
                "summary": "Stars attend gala",
            },
        ]
    )
    assert "Port strike hits Los Angeles" in text
    assert "supply-chain relevant" in text
    assert "Celebrity awards night" not in text


def test_format_for_chat_empty():
    service = NewsService(client=MagicMock())
    assert "could not retrieve" in service.format_for_chat([]).lower()
