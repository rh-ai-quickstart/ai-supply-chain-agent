"""``SupplyChainStateBuilder`` and static fallback (mocked OpenSky)."""

import json
from unittest.mock import MagicMock

import pytest

from clients.opensky_client import OpenSkyClient
from services.supply_chain_state_builder import (
    SupplyChainStateBuilder,
    get_static_fallback_data,
)


@pytest.fixture
def override_config_path(tmp_path, monkeypatch):
    """Point the builder at a temp config file and clear the module cache."""
    import services.supply_chain_state_builder as mod

    path = tmp_path / "config.json"
    monkeypatch.setenv(mod._CONFIG_ENV_VAR, str(path))
    mod._config_cache = None
    yield path
    mod._config_cache = None


def _real_config() -> dict:
    import services.supply_chain_state_builder as mod

    return json.loads(mod._DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))


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


def test_build_state_data_loaded_from_config(override_config_path):
    config = _real_config()
    config["seaFreight"]["ports"].append(
        {"id": "custom", "name": "Custom Port", "lat": 0.0, "lng": 0.0, "risk": 1}
    )
    config["landFreight"]["assets"][0]["name"] = "Custom Truck"
    override_config_path.write_text(json.dumps(config), encoding="utf-8")

    opensky = MagicMock(spec=OpenSkyClient)
    opensky.fetch_states.return_value = None
    state = SupplyChainStateBuilder(opensky_client=opensky).build_state()

    sea_ports = [p["id"] for p in state["mapData"]["global"]["ports"]]
    assert "custom" in sea_ports
    land_assets = state["mapData"]["regional"]["assets"]
    assert land_assets[0]["name"] == "Custom Truck"


def test_static_fallback_data_loaded_from_config(override_config_path):
    config = _real_config()
    config["staticFallback"]["kpis"]["inStock"] = {"value": "42%"}
    override_config_path.write_text(json.dumps(config), encoding="utf-8")

    data = get_static_fallback_data()
    assert data["kpis"]["inStock"]["value"] == "42%"
