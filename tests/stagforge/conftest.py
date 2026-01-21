"""Test fixtures for Stagforge."""

import asyncio
import multiprocessing
import os
import time
from typing import Generator

import httpx
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Set matplotlib backend before any imports (for NiceGUI testing)
os.environ.setdefault('MPLBACKEND', 'Agg')


# =============================================================================
# Unit test fixtures (no browser/server required)
# =============================================================================

@pytest.fixture(scope="module")
def test_client():
    """Create a TestClient for FastAPI unit testing without a server.

    This fixture uses Starlette's TestClient to test API endpoints directly,
    without starting a real HTTP server or NiceGUI application.
    """
    from starlette.testclient import TestClient
    from stagforge.app import create_api_app

    app = create_api_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def api_client(test_client):
    """HTTP client for API requests (uses TestClient for unit testing).

    This fixture wraps TestClient to provide httpx.Client-like interface
    for tests that don't require a full browser session.
    """
    return test_client


def run_server():
    """Run the NiceGUI server in a subprocess."""
    import sys
    from pathlib import Path

    # Import and run main which sets up NiceGUI
    from nicegui import ui, app
    from stagforge.app import create_api_app
    from stagforge.canvas_editor import CanvasEditor

    # Mount the API
    api_app = create_api_app()
    app.mount("/api", api_app)

    # Serve frontend static files
    FRONTEND_DIR = Path(__file__).parent.parent.parent / "stagforge" / "frontend"
    app.add_static_files("/static", FRONTEND_DIR)

    @ui.page("/")
    def index():
        ui.add_head_html('<link rel="stylesheet" href="/static/css/main.css">')
        CanvasEditor(width=800, height=600, api_base="/api").classes("w-full h-full")

    ui.run(host="127.0.0.1", port=8081, reload=False, show=False)


@pytest.fixture(scope="session")
def server_process() -> Generator[multiprocessing.Process, None, None]:
    """Start the server in a subprocess for integration tests.

    NOTE: This fixture starts a real server. Tests using this fixture
    require the server to be accessible and a browser session to be active.
    For unit tests of the Python backend, use mock fixtures instead.
    """
    proc = multiprocessing.Process(target=run_server, daemon=True)
    proc.start()

    # Wait for server to be ready
    base_url = "http://127.0.0.1:8081"
    max_wait = 10
    start = time.time()
    while time.time() - start < max_wait:
        try:
            response = httpx.get(f"{base_url}/api/health", timeout=1)
            if response.status_code == 200:
                break
        except httpx.RequestError:
            pass
        time.sleep(0.1)

    yield proc

    proc.terminate()
    proc.join(timeout=5)


@pytest.fixture(scope="session")
def server_api_client(server_process) -> Generator[httpx.Client, None, None]:
    """HTTP client for API requests against a running server.

    Use this for integration tests that require a full NiceGUI server.
    For unit tests, use `api_client` which uses TestClient.
    """
    with httpx.Client(base_url="http://127.0.0.1:8081/api") as client:
        yield client


@pytest.fixture
def async_client() -> Generator[httpx.AsyncClient, None, None]:
    """Async HTTP client for API requests (no server dependency)."""
    with httpx.AsyncClient(base_url="http://127.0.0.1:8081/api") as client:
        yield client


# Mock fixtures for unit testing without browser session
@pytest.fixture
def mock_session_state():
    """Create a mock session state for unit testing."""
    from stagforge.sessions.models import SessionState, LayerInfo

    return SessionState(
        document_width=800,
        document_height=600,
        active_tool="brush",
        foreground_color="#000000",
        background_color="#FFFFFF",
        zoom=1.0,
        layers=[
            LayerInfo(
                id="layer-1",
                name="Background",
                visible=True,
                locked=False,
                opacity=1.0,
                blend_mode="normal",
            )
        ],
        active_layer_id="layer-1",
    )


# Selenium browser fixtures for UI testing
@pytest.fixture(scope="session")
def chrome_options() -> ChromeOptions:
    """Configure Chrome options for headless testing."""
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # Enable logging for debugging
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    return options


@pytest.fixture(scope="session")
def browser(server_process, chrome_options) -> Generator[webdriver.Chrome, None, None]:
    """Create a Selenium WebDriver for browser testing.

    This fixture starts a headless Chrome browser and navigates to the app.
    """
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)

    # Navigate to the app
    driver.get("http://127.0.0.1:8081")

    # Wait for the editor to load
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "editor-root"))
        )
    except Exception as e:
        print(f"Editor failed to load: {e}")
        print(f"Page source: {driver.page_source[:2000]}")
        raise

    yield driver

    driver.quit()


@pytest.fixture
def fresh_browser(server_process, chrome_options) -> Generator[webdriver.Chrome, None, None]:
    """Create a fresh browser instance for each test (not session-scoped)."""
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)

    driver.get("http://127.0.0.1:8081")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "editor-root"))
        )
    except Exception as e:
        print(f"Editor failed to load: {e}")
        raise

    yield driver

    driver.quit()


class BrowserHelper:
    """Helper class for common browser testing operations."""

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def get_browser_logs(self) -> list:
        """Get browser console logs for debugging."""
        return self.driver.get_log("browser")

    def print_errors(self):
        """Print any JavaScript errors from the browser console."""
        logs = self.get_browser_logs()
        errors = [log for log in logs if log["level"] in ("SEVERE", "WARNING")]
        if errors:
            print("\n=== Browser Console Errors ===")
            for error in errors:
                print(f"  [{error['level']}] {error['message']}")
            print("==============================\n")
        return errors

    def find_by_css(self, selector: str, timeout: float = 10):
        """Find element by CSS selector with wait."""
        return self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def find_clickable(self, selector: str, timeout: float = 10):
        """Find clickable element by CSS selector."""
        return self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )

    def click(self, selector: str):
        """Click an element by CSS selector."""
        element = self.find_clickable(selector)
        element.click()
        return element

    def is_visible(self, selector: str) -> bool:
        """Check if an element is visible."""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            return element.is_displayed()
        except Exception:
            return False

    def wait_for_visible(self, selector: str, timeout: float = 10):
        """Wait for element to become visible."""
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
        )

    def wait_for_invisible(self, selector: str, timeout: float = 10):
        """Wait for element to become invisible."""
        return WebDriverWait(self.driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
        )

    def execute_js(self, script: str, *args):
        """Execute JavaScript in the browser."""
        return self.driver.execute_script(script, *args)

    def get_vue_data(self, property_name: str):
        """Get a property from the Vue component."""
        return self.execute_js(f"""
            const app = document.querySelector('.editor-root').__vue_app__;
            const vm = app._instance?.proxy;
            return vm?.{property_name};
        """)


@pytest.fixture
def browser_helper(browser) -> BrowserHelper:
    """Create a BrowserHelper instance for the session browser."""
    return BrowserHelper(browser)


@pytest.fixture
def fresh_browser_helper(fresh_browser) -> BrowserHelper:
    """Create a BrowserHelper instance for a fresh browser."""
    return BrowserHelper(fresh_browser)


# New unified test helpers
@pytest.fixture
def helpers(browser):
    """Create unified TestHelpers instance for the session browser."""
    from .helpers import TestHelpers
    h = TestHelpers(browser)
    h.editor.wait_for_editor()  # Ensure editor is ready
    return h


@pytest.fixture
def fresh_helpers(fresh_browser):
    """Create unified TestHelpers instance for a fresh browser (per-test)."""
    from .helpers import TestHelpers
    h = TestHelpers(fresh_browser)
    h.editor.wait_for_editor()
    return h


@pytest.fixture
def editor(browser):
    """Create an EditorTestHelper instance for rendering parity tests.

    This is the primary fixture for parity integration tests.
    Uses session-scoped browser for efficiency.
    """
    from .helpers.editor import EditorTestHelper
    helper = EditorTestHelper(browser)
    helper.wait_for_editor()
    return helper


@pytest.fixture
def fresh_editor(fresh_browser):
    """Create a fresh EditorTestHelper instance for each test.

    Use this when tests need a clean slate (no leftover layers/state).
    """
    from .helpers.editor import EditorTestHelper
    helper = EditorTestHelper(fresh_browser)
    helper.wait_for_editor()
    return helper


# =============================================================================
# Playwright-based Screen fixture (NiceGUI Screen API compatible)
# =============================================================================

class Screen:
    """Playwright-based screen fixture mimicking NiceGUI's Screen API.

    Provides a similar interface to NiceGUI's Screen fixture but uses
    Playwright instead of Selenium for better cross-platform support.
    """

    def __init__(self, page, base_url: str = "http://127.0.0.1:8081"):
        self.page = page
        self.base_url = base_url

    def open(self, path: str = "/"):
        """Navigate to a path."""
        url = f"{self.base_url}{path}" if path.startswith("/") else path
        self.page.goto(url)

    def should_contain(self, text: str, timeout: float = 5.0):
        """Assert that the page contains the given text."""
        self.page.wait_for_selector(f"text={text}", timeout=timeout * 1000)

    def should_not_contain(self, text: str, timeout: float = 0.5):
        """Assert that the page does not contain the given text."""
        try:
            self.page.wait_for_selector(f"text={text}", timeout=timeout * 1000)
            raise AssertionError(f"Page should not contain '{text}'")
        except Exception:
            pass  # Expected - text not found

    def wait(self, seconds: float):
        """Wait for a number of seconds."""
        self.page.wait_for_timeout(seconds * 1000)

    def click(self, selector: str):
        """Click an element by selector."""
        self.page.click(selector)

    def type(self, selector: str, text: str):
        """Type text into an element."""
        self.page.fill(selector, text)

    def find(self, selector: str):
        """Find an element by selector."""
        return self.page.query_selector(selector)

    def find_all(self, selector: str):
        """Find all elements matching selector."""
        return self.page.query_selector_all(selector)

    def execute_script(self, script: str, *args):
        """Execute JavaScript in the browser (Selenium-compatible name)."""
        return self.page.evaluate(script, args if args else None)

    def wait_for_editor(self, timeout: float = 15.0):
        """Wait for the Slopstag editor to fully load."""
        self.page.wait_for_selector('.editor-root', timeout=timeout * 1000)
        self.page.wait_for_function(
            "() => window.__stagforge_app__?.layerStack?.layers?.length > 0",
            timeout=timeout * 1000
        )


@pytest.fixture(scope="module")
def playwright_browser():
    """Launch Playwright browser for the test module."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def screen(playwright_browser):
    """Create a Screen instance for each test.

    This fixture provides a NiceGUI Screen-like API using Playwright.
    Usage:
        def test_something(screen):
            screen.open('/')
            screen.wait_for_editor()
            screen.should_contain('Canvas')
    """
    page = playwright_browser.new_page()
    s = Screen(page)
    yield s
    page.close()
