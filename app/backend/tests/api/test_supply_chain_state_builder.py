"""``SupplyChainStateBuilder`` and static fallback (mocked OpenSky)."""

from unittest.mock import MagicMock

import pytest

from clients.opensky_client import OpenSkyClient
from services.supply_chain_state_builder import (
    SupplyChainStateBuilder,
    get_static_fallback_data,
)


def test_get_static_fallback_data_shape():
    data = get_static_fallback_data()
    assert set(data.keys()) >= {"kpis", "alerts", "charts", "mapData"}
    assert "global" in data["mapData"]


def test_air_aggregator_fallback_when_no_live_planes():
    opensky = MagicMock(spec=OpenSkyClient)
    opensky.fetch_states.return_value = None
    builder = SupplyChainStateBuilder(opensky_client=opensky)
    state = builder.build_state()
    assert "kpis" in state
    air = state["mapData"]["airFreight"]
    assert len(air["assets"]) > 0
    assert any("Sim" in a.get("name", "") or "Gen" in a.get("name", "") for a in air["assets"])


@pytest.mark.usefixtures("reset_supply_chain_event_slot")
def test_trigger_event_returns_build_state():
    opensky = MagicMock(spec=OpenSkyClient)
    opensky.fetch_states.return_value = None
    builder = SupplyChainStateBuilder(opensky_client=opensky)
    out = builder.trigger_event("regional")
    assert "mapData" in out
