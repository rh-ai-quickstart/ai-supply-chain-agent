"""
Chat UI E2E tests — off-topic guardrail (parity with kind-verify-deployment.sh).
"""

import os
import re
import time

import pytest
from playwright.sync_api import Page, expect

TEST_TIMEOUT = 60000
CHAT_RESPONSE_TIMEOUT = int(os.getenv("E2E_CHAT_TIMEOUT_MS", "120000"))


def _send_chat_message(page: Page, message: str) -> None:
    chat_input = page.get_by_label("Chat input")
    expect(chat_input).to_be_visible(timeout=TEST_TIMEOUT)
    chat_input.fill(message)
    chat_input.press("Enter")
    expect(page.get_by_role("heading", name="AI Assistant")).to_be_visible(
        timeout=TEST_TIMEOUT
    )


def _wait_for_ai_reply(page: Page, pattern: re.Pattern[str]) -> None:
    """Wait until an AI bubble contains text matching pattern."""
    deadline = time.time() + (CHAT_RESPONSE_TIMEOUT / 1000)
    last_error = None
    while time.time() < deadline:
        try:
            ai_messages = page.locator(".chat-message.ai")
            expect(ai_messages.last).to_be_visible(timeout=5000)
            text = ai_messages.last.inner_text()
            if pattern.search(text):
                return
        except Exception as exc:  # noqa: BLE001 - playwright locator errors are transient during polling
            last_error = exc
        if page.get_by_text("Thinking…", exact=False).is_visible():
            time.sleep(1)
            continue
        if page.locator(".chat-log-display .error").count() > 0:
            err = page.locator(".chat-log-display .error").first.inner_text()
            pytest.fail(f"Chat error displayed: {err}")
        time.sleep(1)
    raise AssertionError(
        f"Timed out waiting for AI reply matching {pattern.pattern!r}. Last error: {last_error}"
    )


@pytest.mark.skipif(
    os.getenv("SKIP_MODEL_TESTS", "false").lower() == "true",
    reason="Chat tests disabled via SKIP_MODEL_TESTS",
)
class TestChatUI:
    def test_guardrail_blocks_off_topic_prompt(self, page: Page):
        _send_chat_message(page, "Where is the best pizza?")
        _wait_for_ai_reply(page, re.compile(r"supply chain", re.IGNORECASE))
        expect(page.locator(".chat-message.human").last).to_contain_text("pizza")

    def test_clear_conversation_removes_messages_keeps_scenario_context(self, page: Page):
        """Clearing the conversation drops user/AI bubbles but keeps the KB context."""
        # Confirm the knowledge base status is visible before chatting.
        kb_status = page.locator(".chat-kb-status__text").first
        expect(kb_status).to_be_visible(timeout=TEST_TIMEOUT)
        kb_before = kb_status.inner_text()
        assert kb_before.startswith("Knowledge base:")

        _send_chat_message(page, "Where is the best pizza?")
        _wait_for_ai_reply(page, re.compile(r"supply chain", re.IGNORECASE))
        expect(page.locator(".chat-message.human").last).to_contain_text("pizza")

        # The modal auto-opens after a reply; the clear button lives in the header.
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=TEST_TIMEOUT)
        clear_button = dialog.get_by_role("button", name="Clear conversation", exact=True)
        expect(clear_button).to_be_visible(timeout=TEST_TIMEOUT)
        expect(page.locator(".chat-message.human")).to_have_count(1)

        clear_button.click()

        # Conversation is reset to the empty state.
        expect(page.get_by_text("No chat messages yet.")).to_be_visible(timeout=TEST_TIMEOUT)
        expect(page.locator(".chat-message.human")).to_have_count(0)

        # The scenario context (KB status) from before the chat still shows.
        expect(page.locator(".chat-kb-status__text").first).to_have_text(kb_before)
