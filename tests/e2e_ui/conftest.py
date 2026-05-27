"""
Pytest configuration for Playwright UI E2E tests.

Patterns adapted from the RAG quickstart (tests/e2e_ui/conftest.py).
"""

from __future__ import annotations

import os
import time

import pytest
import requests
from playwright.sync_api import Page

SUPPLY_CHAIN_UI_ENDPOINT = os.getenv(
    "SUPPLY_CHAIN_UI_ENDPOINT", "http://127.0.0.1:18080"
).rstrip("/")
BACKEND_HEALTH_URL = os.getenv(
    "BACKEND_HEALTH_URL", "http://127.0.0.1:15001/healthz"
)
TEST_TIMEOUT_MS = int(os.getenv("E2E_TEST_TIMEOUT_MS", "60000"))


def wait_for_service(url: str, name: str, max_retries: int = 30, retry_delay: int = 2) -> bool:
    print(f"Waiting for {name} at {url}...")
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in (200, 404):
                print(f"{name} is ready.")
                return True
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                print(f"  attempt {attempt + 1}/{max_retries} failed, retrying...")
                time.sleep(retry_delay)
    return False


@pytest.fixture(scope="session", autouse=True)
def check_services():
    """Skip the suite if the dashboard UI is not reachable."""
    ui_ready = wait_for_service(f"{SUPPLY_CHAIN_UI_ENDPOINT}/", "Supply Chain UI", max_retries=15)
    if not ui_ready:
        pytest.skip(f"UI not available at {SUPPLY_CHAIN_UI_ENDPOINT}")

    if not wait_for_service(BACKEND_HEALTH_URL, "Backend health", max_retries=10):
        print(f"Warning: backend health check failed at {BACKEND_HEALTH_URL}")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
    }


@pytest.fixture(autouse=True)
def open_dashboard(page: Page):
    """Navigate to the dashboard before each test."""
    page.set_default_timeout(TEST_TIMEOUT_MS)
    last_exc = None
    for attempt in range(3):
        try:
            page.goto(
                SUPPLY_CHAIN_UI_ENDPOINT + "/",
                timeout=60000,
                wait_until="domcontentloaded",
            )
            page.wait_for_load_state("load", timeout=60000)
            page.get_by_role("heading", name="Supply Chain Command Center").wait_for(
                state="visible", timeout=TEST_TIMEOUT_MS
            )
            break
        except Exception as exc:
            last_exc = exc
            if attempt == 2:
                raise
            print(f"Navigation attempt {attempt + 1} failed: {exc}, retrying...")
            time.sleep(2)
    else:
        if last_exc:
            raise last_exc
    yield
