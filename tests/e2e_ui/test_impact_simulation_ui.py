"""
Impact Simulation UI smoke tests — header, nav, query panel, chat chrome.
"""

from playwright.sync_api import Page, expect

TEST_TIMEOUT = 60000


class TestImpactSimulationUIBasics:
    def test_page_title_visible(self, page: Page):
        title = page.get_by_role("heading", name="Supply Chain Command Center")
        expect(title).to_be_visible(timeout=TEST_TIMEOUT)

    def test_main_navigation_visible(self, page: Page):
        nav = page.get_by_role("navigation", name="Main")
        expect(nav).to_be_visible(timeout=TEST_TIMEOUT)
        expect(nav.get_by_role("button", name="Simulation", exact=True)).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(nav.get_by_role("button", name="Knowledge bases", exact=True)).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(nav.get_by_role("button", name="Create scenario", exact=True)).to_be_visible(
            timeout=TEST_TIMEOUT
        )

    def test_impact_query_panel_visible(self, page: Page):
        expect(page.get_by_role("heading", name="Impact Query")).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(page.get_by_role("button", name="Live Flights")).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(page.get_by_role("button", name="Scenario focus")).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(page.get_by_role("button", name="Run impact query")).to_be_visible(
            timeout=TEST_TIMEOUT
        )

    def test_map_view_defaults_to_live_flights(self, page: Page):
        live = page.get_by_role("button", name="Live Flights")
        expect(live).to_have_attribute("aria-pressed", "true", timeout=TEST_TIMEOUT)

    def test_chat_input_visible(self, page: Page):
        chat_input = page.get_by_label("Chat input")
        expect(chat_input).to_be_visible(timeout=TEST_TIMEOUT)
        expect(chat_input).to_have_attribute("placeholder", "Ask me anything...")

    def test_create_scenario_nav(self, page: Page):
        page.get_by_role("navigation", name="Main").get_by_role(
            "button", name="Create scenario", exact=True
        ).click()
        expect(page.get_by_role("heading", name="Create scenario")).to_be_visible(
            timeout=TEST_TIMEOUT
        )
