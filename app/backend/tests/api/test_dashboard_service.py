"""``DashboardService`` scenario branches (mocked state builder)."""

from unittest.mock import MagicMock

from services.dashboard_service import DashboardService


def test_get_state_delegates_to_builder():
    builder = MagicMock()
    builder.build_state.return_value = {"kpis": {"k": 1}}
    svc = DashboardService(state_builder=builder)
    assert svc.get_state() == {"kpis": {"k": 1}}
    builder.build_state.assert_called_once()


def test_simulate_port_strike_mutates_kpis():
    builder = MagicMock()
    builder.build_state.return_value = {
        "kpis": {"lostSales": {"value": "$0", "trendSymbol": "▼", "trendClass": "down"}},
        "alerts": {"global": []},
        "charts": {"revenue": {"revenueData": [1, 2], "colors": ["green"]}},
    }
    svc = DashboardService(state_builder=builder)
    out = svc.simulate("port-strike", optimize=False)
    assert "SIMULATION: Port Strike" in out["alerts"]["global"][0]["text"]
    assert out["kpis"]["lostSales"]["value"] == "$4.2M"
    assert out["charts"]["revenue"]["colors"] == ["red"] * 5


def test_simulate_geopolitical_branch():
    builder = MagicMock()
    builder.build_state.return_value = {
        "kpis": {"turnover": {"value": "9x", "trendSymbol": "▲", "trendClass": "up"}},
        "alerts": {"global": []},
        "charts": {},
    }
    svc = DashboardService(state_builder=builder)
    out = svc.simulate("geopolitical", optimize=False)
    assert out["kpis"]["turnover"]["value"] == "3.1x"
    assert "Suez" in out["alerts"]["global"][0]["text"]


def test_simulate_uses_static_fallback_when_builder_raises():
    builder = MagicMock()
    builder.build_state.side_effect = RuntimeError("opensky")
    svc = DashboardService(state_builder=builder)
    out = svc.simulate("none", optimize=False)
    assert "kpis" in out
    assert "mapData" in out
