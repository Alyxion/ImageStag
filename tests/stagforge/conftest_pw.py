"""Pytest fixtures for Playwright-based Stagforge tests.

This module provides fixtures for async Playwright tests using pytest-asyncio
and pytest-playwright. The tests use the async Playwright API.

Usage:
    pytest tests/stagforge/test_*_pw.py -v

Set environment variables:
    STAGFORGE_TEST_URL: Base URL of the server (default: http://127.0.0.1:8080)
    STAGFORGE_TEST_SERVER: Set to "0" to skip auto-starting server
"""

import asyncio
import subprocess
import time
import signal
import os
from typing import Generator, AsyncGenerator
import pytest
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from .helpers_pw import TestHelpers


# Default base URL for tests
BASE_URL = os.environ.get("STAGFORGE_TEST_URL", "http://127.0.0.1:8080")


@pytest.fixture(scope="session")
async def browser() -> AsyncGenerator[Browser, None]:
    """Create a browser instance for the test session."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-gpu', '--no-sandbox']
        )
        yield browser
        await browser.close()


@pytest.fixture(scope="function")
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Create a fresh browser context for each test."""
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 900}
    )
    yield context
    await context.close()


@pytest.fixture(scope="function")
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Create a fresh page for each test."""
    page = await context.new_page()
    yield page
    await page.close()


@pytest.fixture(scope="function")
async def helpers(page: Page) -> TestHelpers:
    """Create test helpers with the page and navigate to editor."""
    helpers = TestHelpers(page, BASE_URL)
    await helpers.navigate_to_editor()
    return helpers


@pytest.fixture(scope="session")
def server_process() -> Generator[subprocess.Popen, None, None]:
    """
    Start the Stagforge server for the test session.

    Set STAGFORGE_TEST_SERVER=0 to skip server startup (use existing server).
    """
    if os.environ.get("STAGFORGE_TEST_SERVER", "1") == "0":
        yield None
        return

    # Start server
    env = os.environ.copy()
    env["STAGFORGE_PORT"] = "8080"

    proc = subprocess.Popen(
        ["python", "-m", "stagforge.main"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid if os.name != 'nt' else None
    )

    # Wait for server to be ready
    import httpx
    max_wait = 30
    start = time.time()
    while time.time() - start < max_wait:
        try:
            response = httpx.get(f"{BASE_URL}/api/status", timeout=1)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError(f"Server failed to start within {max_wait}s")

    yield proc

    # Cleanup
    if os.name != 'nt':
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    else:
        proc.terminate()
    proc.wait()


@pytest.fixture(scope="function")
async def helpers_with_server(server_process, page: Page) -> TestHelpers:
    """
    Create test helpers with server management.

    Use this fixture when you want the server to be automatically started.
    """
    helpers = TestHelpers(page, BASE_URL)
    await helpers.navigate_to_editor()
    return helpers


# Mark all tests in this module as requiring playwright
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "playwright: mark test as requiring playwright"
    )
