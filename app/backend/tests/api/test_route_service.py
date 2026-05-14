"""Tests for ``RouteService`` keyword detection and route payloads."""

from services.route_service import ROUTE_KEYWORDS, RouteService


def test_is_route_query_detects_keywords():
    svc = RouteService()
    for kw in ROUTE_KEYWORDS:
        assert svc.is_route_query(f"Please help with {kw} planning")


def test_is_route_query_negative():
    svc = RouteService()
    assert not svc.is_route_query("What is our inventory at Chicago?")


def test_get_optimized_route_default_corridor():
    svc = RouteService()
    out = svc.get_optimized_route("optimize routing from nowhere to nowhere")
    assert "answer" in out
    assert out["routeData"]["type"] == "optimized_land_route"
    assert len(out["routeData"]["coordinates"]) == 2


def test_get_optimized_route_newark_dallas_branch():
    svc = RouteService()
    out = svc.get_optimized_route("truck route from newark hub to dallas dc")
    assert "Newark" in out["answer"] or "newark" in out["answer"].lower()
    assert "Dallas" in out["answer"] or "dallas" in out["answer"].lower()
