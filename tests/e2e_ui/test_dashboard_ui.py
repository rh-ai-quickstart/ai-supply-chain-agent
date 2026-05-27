"""
Dashboard UI smoke tests — load, navigation chrome, KPI bar, simulation panel.
"""

from playwright.sync_api import Page, expect

TEST_TIMEOUT = 60000


class TestDashboardUIBasics:
    def test_page_title_visible(self, page: Page):
        title = page.get_by_role("heading", name="Supply Chain Command Center")
        expect(title).to_be_visible(timeout=TEST_TIMEOUT)

    def test_main_navigation_visible(self, page: Page):
        nav = page.get_by_role("navigation", name="Main")
        expect(nav).to_be_visible(timeout=TEST_TIMEOUT)
        # Scope to nav: "Live Dashboard" also matches substring "Dashboard".
        expect(nav.get_by_role("button", name="Dashboard", exact=True)).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(nav.get_by_role("button", name="Knowledge bases", exact=True)).to_be_visible(
            timeout=TEST_TIMEOUT
        )

    def test_simulation_panel_visible(self, page: Page):
        expect(page.get_by_role("heading", name="AI Simulation & Presets")).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(page.get_by_role("button", name="Live Dashboard")).to_be_visible(
            timeout=TEST_TIMEOUT
        )

    def test_kpi_bar_shows_labels(self, page: Page):
        expect(page.get_by_text("In-Stock Rate", exact=False)).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(page.get_by_text("On-Time Delivery", exact=False)).to_be_visible(
            timeout=TEST_TIMEOUT
        )

    def test_chat_input_visible(self, page: Page):
        chat_input = page.get_by_label("Chat input")
        expect(chat_input).to_be_visible(timeout=TEST_TIMEOUT)
        expect(chat_input).to_have_attribute("placeholder", "Ask me anything...")
