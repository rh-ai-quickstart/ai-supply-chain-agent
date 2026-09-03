"""
Impact Simulation UI smoke tests — header, nav, query panel, chat chrome.
"""

import re

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
        expect(nav.get_by_role("button", name="Create scenario")).to_have_count(0)

    def test_impact_query_panel_visible(self, page: Page):
        expect(page.get_by_role("heading", name="Scenario Selection")).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(page.get_by_role("button", name="All Flights")).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(page.get_by_role("button", name="Scenario focus")).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(page.get_by_role("button", name="Run Scenario")).to_have_count(0)

    def test_map_view_defaults_to_live_flights(self, page: Page):
        live = page.get_by_role("button", name="All Flights")
        expect(live).to_have_attribute("aria-pressed", "true", timeout=TEST_TIMEOUT)

    def test_chat_input_visible(self, page: Page):
        chat_input = page.get_by_label("Chat input")
        expect(chat_input).to_be_visible(timeout=TEST_TIMEOUT)
        expect(chat_input).to_have_attribute("placeholder", "Ask me anything...")
        expect(page.get_by_role("status").filter(has_text="Knowledge base:")).to_be_visible(
            timeout=TEST_TIMEOUT
        )

class TestImpactSimulationQueryFlow:
    def test_suggested_prompts_visible_after_scenario_load(self, page: Page):
        page.get_by_text("Loading scenarios…").wait_for(state="hidden", timeout=TEST_TIMEOUT)
        expect(page.get_by_text("No scenarios available")).to_have_count(0)

        scenario_group = page.locator(
            "[role='group'][aria-labelledby='impact-scenario-label']"
        )
        uk_closure = scenario_group.get_by_role("button", name="UK Airspace Closure")
        expect(uk_closure).to_be_visible(timeout=TEST_TIMEOUT)
        uk_closure.click()
        expect(page.get_by_role("heading", name="Suggested prompts")).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(
            page.get_by_role("button", name="Show affected aircraft and recommend diversions.")
        ).to_be_visible(timeout=TEST_TIMEOUT)

    def test_create_scenario_modal_propose_fields(self, page: Page):
        page.get_by_role("button", name="Create scenario", exact=True).click()
        dialog = page.get_by_role("dialog", name="Create scenario")
        expect(dialog).to_be_visible(timeout=TEST_TIMEOUT)
        description = dialog.get_by_label("Disruption description")
        expect(description).to_be_visible()
        expect(dialog.get_by_role("button", name="Propose scenario")).to_be_visible(
            timeout=TEST_TIMEOUT
        )


class TestImpactSimulationNavigation:
    def test_knowledge_bases_nav_from_simulation(self, page: Page):
        page.get_by_role("button", name="Knowledge bases", exact=True).click()
        expect(page).to_have_url(re.compile(r"#/knowledge-bases"), timeout=TEST_TIMEOUT)
