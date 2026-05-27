"""
Knowledge bases view UI smoke tests.
"""

import os

from playwright.sync_api import Page, expect

SUPPLY_CHAIN_UI_ENDPOINT = os.getenv(
    "SUPPLY_CHAIN_UI_ENDPOINT", "http://127.0.0.1:18080"
).rstrip("/")

TEST_TIMEOUT = 60000


class TestKnowledgeBasesUI:
    def test_navigate_via_header_button(self, page: Page):
        page.get_by_role("button", name="Knowledge bases").click()
        expect(page.get_by_role("heading", name="Create knowledge base")).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(
            page.get_by_role("heading", name="Registered knowledge bases")
        ).to_be_visible(timeout=TEST_TIMEOUT)

    def test_direct_hash_route(self, page: Page):
        page.goto(f"{SUPPLY_CHAIN_UI_ENDPOINT}/#/knowledge-bases", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Create knowledge base")).to_be_visible(
            timeout=TEST_TIMEOUT
        )
        expect(page.get_by_label("Display name")).to_be_visible(timeout=TEST_TIMEOUT)
        expect(page.get_by_label("Documents")).to_be_visible(timeout=TEST_TIMEOUT)
