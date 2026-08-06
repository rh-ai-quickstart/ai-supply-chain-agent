"""``FlightTrackingService`` OpenSky state-vector normalization."""

from unittest.mock import MagicMock

from clients.opensky_client import OpenSkyClient
from services.flight_tracking_service import FlightTrackingService

CARGO_WATCHLIST = ["FDX", "UPS"]


def _state(
    icao24="abc123",
    callsign="FDX123",
    on_ground=False,
    lon=10.0,
    lat=20.0,
    baro_altitude=9000,
    velocity=250.0,
    track=90,
):
    """Build a 17-field OpenSky state vector (only fields we read matter)."""
    row = [None] * 17
    row[0] = icao24
    row[1] = callsign
    row[5] = lon
    row[6] = lat
    row[7] = baro_altitude
    row[8] = on_ground
    row[9] = velocity
    row[10] = track
    return row


def test_returns_empty_list_when_opensky_has_no_data():
    opensky = MagicMock(spec=OpenSkyClient)
    opensky.fetch_states.return_value = None
    service = FlightTrackingService(opensky, CARGO_WATCHLIST)
    assert service.get_live_planes() == []


def test_matches_cargo_watchlist_by_callsign_prefix():
    opensky = MagicMock(spec=OpenSkyClient)
    opensky.fetch_states.return_value = [_state(callsign="FDX456")]
    service = FlightTrackingService(opensky, CARGO_WATCHLIST)
    planes = service.get_live_planes()
    assert len(planes) == 1
    assert planes[0]["cargo"] == "Mixed Freight"
    assert "(Live)" in planes[0]["name"]


def test_skips_flights_on_ground():
    opensky = MagicMock(spec=OpenSkyClient)
    opensky.fetch_states.return_value = [_state(callsign="FDX456", on_ground=True)]
    service = FlightTrackingService(opensky, CARGO_WATCHLIST)
    assert service.get_live_planes() == []


def test_fills_with_general_traffic_below_target_density():
    opensky = MagicMock(spec=OpenSkyClient)
    opensky.fetch_states.return_value = [
        _state(icao24="a1", callsign="FDX1"),
        _state(icao24="a2", callsign="XYZ999", velocity=300.0),
    ]
    service = FlightTrackingService(opensky, CARGO_WATCHLIST)
    planes = service.get_live_planes(target_density=100)
    assert len(planes) == 2
    names = {p["name"] for p in planes}
    assert any("(Live)" in n for n in names)
    assert any("(General)" in n for n in names)


def test_general_traffic_excludes_slow_flights():
    opensky = MagicMock(spec=OpenSkyClient)
    opensky.fetch_states.return_value = [_state(icao24="a2", callsign="XYZ999", velocity=50.0)]
    service = FlightTrackingService(opensky, CARGO_WATCHLIST)
    assert service.get_live_planes() == []


def test_malformed_state_vector_is_skipped_and_recorded():
    opensky = MagicMock(spec=OpenSkyClient)
    opensky.fetch_states.return_value = [None, _state(callsign="FDX1")]
    service = FlightTrackingService(opensky, CARGO_WATCHLIST)
    planes = service.get_live_planes()
    assert len(planes) == 1
    assert service.skipped_count >= 1


def test_general_traffic_does_not_duplicate_cargo_matches():
    opensky = MagicMock(spec=OpenSkyClient)
    opensky.fetch_states.return_value = [_state(icao24="a1", callsign="FDX1", velocity=300.0)]
    service = FlightTrackingService(opensky, CARGO_WATCHLIST)
    planes = service.get_live_planes(target_density=100)
    assert len(planes) == 1
