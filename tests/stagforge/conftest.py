"""Test fixtures for Stagforge.

Provides three levels of test fixtures:
1. Unit tests (no server): Use `test_client` or `api_client`
2. Integration tests (server + API): Use `server` + `http_client`
3. Browser tests (server + browser): Use `helpers` (Playwright) or `selenium_browser` (Selenium)
"""

import os
import signal
import subprocess
import sys
import time
from typing import Generator, AsyncGenerator

import httpx
import pytest

# Set matplotlib backend before any imports (for NiceGUI testing)
os.environ.setdefault('MPLBACKEND', 'Agg')

# Server configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = int(os.environ.get("STAGFORGE_TEST_PORT", "8080"))
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"


# =============================================================================
# Server Process Management
# =============================================================================

def _wait_for_server(url: str, timeout: float = 20.0, interval: float = 0.3) -> bool:
    """Wait for server to become ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = httpx.get(f"{url}/api/health", timeout=2.0)
            if response.status_code == 200:
                return True
        except (httpx.RequestError, httpx.TimeoutException):
            pass
        time.sleep(interval)
    return False


@pytest.fixture(scope="session")
def server() -> Generator[str, None, None]:
    """Start NiceGUI server for the test session.

    Yields the base URL of the running server.

    Usage:
        def test_something(server, http_client):
            response = http_client.get("/api/health")
            assert response.status_code == 200
    """
    # Check if server is already running (e.g., started manually for development)
    if os.environ.get("STAGFORGE_TEST_SERVER", "1") == "0":
        yield SERVER_URL
        return

    # Check if server is already running on the port
    try:
        response = httpx.get(f"{SERVER_URL}/api/health", timeout=1.0)
        if response.status_code == 200:
            # Server already running, use it
            yield SERVER_URL
            return
    except (httpx.RequestError, httpx.TimeoutException):
        pass

    # Start server using subprocess (more robust than multiprocessing for NiceGUI)
    env = os.environ.copy()
    env["STAGFORGE_PORT"] = str(SERVER_PORT)
    # Tell NiceGUI not to use test mode (it checks for pytest in argv)
    env["NICEGUI_SCREEN_TEST_PORT"] = str(SERVER_PORT)

    proc = subprocess.Popen(
        [sys.executable, "-m", "stagforge.main"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        # Use process group for clean termination on Unix
        preexec_fn=os.setsid if os.name != 'nt' else None,
    )

    # Wait for server to be ready
    if not _wait_for_server(SERVER_URL):
        # Get error output for debugging
        proc.terminate()
        try:
            _, stderr = proc.communicate(timeout=5)
            error_msg = stderr.decode()[:1000] if stderr else "No error output"
        except Exception:
            error_msg = "Could not get error output"
        pytest.fail(f"Server failed to start at {SERVER_URL}. Error: {error_msg}")

    yield SERVER_URL

    # Cleanup - terminate the process group
    if os.name != 'nt':
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
    else:
        proc.terminate()

    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name != 'nt':
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
        proc.wait(timeout=2)


# =============================================================================
# HTTP Client Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def test_client():
    """TestClient for FastAPI unit testing without a server.

    Use this for testing API endpoints directly without HTTP overhead.
    """
    from starlette.testclient import TestClient
    from stagforge.app import create_api_app

    app = create_api_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def api_client(test_client):
    """Alias for test_client (backwards compatibility)."""
    return test_client


@pytest.fixture(scope="session")
def http_client(server: str) -> Generator[httpx.Client, None, None]:
    """HTTP client for API requests against running server.

    Use this for integration tests that need the full server stack.
    """
    with httpx.Client(base_url=f"{server}/api", timeout=30.0) as client:
        yield client


# =============================================================================
# Mock Fixtures (for unit testing without browser)
# =============================================================================

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


# =============================================================================
# Playwright Fixtures (async, for *_pw.py tests)
# =============================================================================

from playwright.async_api import (
    async_playwright,
    Page as AsyncPage,
    Browser as AsyncBrowser,
    BrowserContext as AsyncBrowserContext,
)


@pytest.fixture(scope="session")
def _ensure_server(server: str) -> str:
    """Ensure server is running (bridge for async fixtures)."""
    return server


@pytest.fixture(scope="function")
async def pw_browser(_ensure_server: str) -> AsyncGenerator[AsyncBrowser, None]:
    """Playwright browser instance for each test function.

    Note: Using function scope due to pytest-asyncio limitations with session-scoped
    async fixtures. Playwright browser startup is fast enough that this is acceptable.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
        )
        yield browser
        await browser.close()


@pytest.fixture(scope="function")
async def pw_context(pw_browser: AsyncBrowser) -> AsyncGenerator[AsyncBrowserContext, None]:
    """Fresh browser context for each test."""
    context = await pw_browser.new_context(
        viewport={'width': 1280, 'height': 900}
    )
    yield context
    await context.close()


@pytest.fixture(scope="function")
async def pw_page(pw_context: AsyncBrowserContext) -> AsyncGenerator[AsyncPage, None]:
    """Fresh page for each test."""
    page = await pw_context.new_page()
    yield page
    await page.close()


@pytest.fixture(scope="function")
async def helpers(pw_page: AsyncPage, _ensure_server: str):
    """Test helpers with page, navigated to editor.

    This is the primary fixture for Playwright-based tests.

    Usage:
        async def test_something(helpers):
            await helpers.new_document(800, 600)
            layer_info = await helpers.editor.get_layer_info(index=0)
    """
    from .helpers_pw import TestHelpers
    h = TestHelpers(pw_page, _ensure_server)
    await h.navigate_to_editor()
    return h


# =============================================================================
# Selenium Fixtures (sync, for legacy tests)
# =============================================================================

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


@pytest.fixture(scope="session")
def chrome_options() -> ChromeOptions:
    """Chrome options for headless testing."""
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    return options


@pytest.fixture(scope="session")
def selenium_browser(server: str, chrome_options: ChromeOptions) -> Generator[webdriver.Chrome, None, None]:
    """Selenium WebDriver for browser testing.

    Use this for tests that require Selenium (legacy tests).
    New tests should prefer Playwright fixtures.
    """
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)

    # Navigate to app
    driver.get(server)

    # Wait for editor to load
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "editor-root"))
        )
    except Exception as e:
        print(f"Editor failed to load: {e}")
        print(f"Page source: {driver.page_source[:2000]}")
        driver.quit()
        raise

    yield driver

    driver.quit()


@pytest.fixture
def fresh_browser(server: str, chrome_options: ChromeOptions) -> Generator[webdriver.Chrome, None, None]:
    """Fresh Selenium browser for each test."""
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)

    driver.get(server)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "editor-root"))
        )
    except Exception as e:
        print(f"Editor failed to load: {e}")
        driver.quit()
        raise

    yield driver

    driver.quit()


# =============================================================================
# Selenium Helper Classes
# =============================================================================

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
def browser_helper(selenium_browser) -> BrowserHelper:
    """BrowserHelper for session Selenium browser."""
    return BrowserHelper(selenium_browser)


@pytest.fixture
def fresh_browser_helper(fresh_browser) -> BrowserHelper:
    """BrowserHelper for fresh browser (per-test)."""
    return BrowserHelper(fresh_browser)


# =============================================================================
# Editor Test Helpers (Selenium)
# =============================================================================

@pytest.fixture
def selenium_helpers(selenium_browser):
    """TestHelpers for session Selenium browser."""
    from .helpers import TestHelpers
    h = TestHelpers(selenium_browser)
    h.editor.wait_for_editor()
    return h


@pytest.fixture
def fresh_helpers(fresh_browser):
    """TestHelpers for fresh browser (per-test)."""
    from .helpers import TestHelpers
    h = TestHelpers(fresh_browser)
    h.editor.wait_for_editor()
    return h


@pytest.fixture
def editor(selenium_browser):
    """EditorTestHelper for rendering parity tests."""
    from .helpers.editor import EditorTestHelper
    helper = EditorTestHelper(selenium_browser)
    helper.wait_for_editor()
    return helper


@pytest.fixture
def fresh_editor(fresh_browser):
    """Fresh EditorTestHelper for each test."""
    from .helpers.editor import EditorTestHelper
    helper = EditorTestHelper(fresh_browser)
    helper.wait_for_editor()
    return helper


# =============================================================================
# Playwright Sync Fixtures (for non-async tests)
# =============================================================================

class Screen:
    """Playwright-based screen fixture mimicking NiceGUI's Screen API."""

    def __init__(self, page, base_url: str = SERVER_URL):
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
            pass

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
        """Execute JavaScript in the browser."""
        return self.page.evaluate(script, args if args else None)

    def wait_for_editor(self, timeout: float = 15.0):
        """Wait for the Stagforge editor to fully load."""
        self.page.wait_for_selector('.editor-root', timeout=timeout * 1000)
        self.page.wait_for_function(
            "() => window.__stagforge_app__?.layerStack?.layers?.length > 0",
            timeout=timeout * 1000
        )


@pytest.fixture(scope="module")
def playwright_browser(server: str):
    """Sync Playwright browser for module."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def screen(playwright_browser):
    """Screen instance for NiceGUI-style tests."""
    page = playwright_browser.new_page()
    s = Screen(page)
    yield s
    page.close()


# =============================================================================
# Backwards Compatibility Aliases
# =============================================================================

# Old fixture names that may be used in existing tests
server_process = server  # Alias for backwards compatibility
server_api_client = http_client  # Alias for backwards compatibility
