"""``OpenSkyClient`` HTTP behavior with a mocked ``requests.Session``."""

from unittest.mock import MagicMock

from clients.opensky_client import OpenSkyClient


def test_fetch_states_caches_successful_response():
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"states": [[None] * 17]}
    session.get.return_value = response

    client = OpenSkyClient(session=session)
    first = client.fetch_states()
    second = client.fetch_states()
    assert first is second
    assert session.get.call_count == 1


def test_fetch_states_returns_stale_cache_on_http_error():
    session = MagicMock()
    ok = MagicMock()
    ok.status_code = 200
    ok.json.return_value = {"states": [["icao", "FDX123", None, None, None, 0, 0, 0, False, 200, 0, 0]]}
    bad = MagicMock()
    bad.status_code = 503

    session.get.side_effect = [ok, bad]
    client = OpenSkyClient(session=session)
    assert client.fetch_states() is not None
    assert client.fetch_states() is not None
