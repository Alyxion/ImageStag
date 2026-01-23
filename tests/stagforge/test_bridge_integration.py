"""Integration tests for the WebSocket bridge using Playwright.

Tests both client (JavaScript) and server (Python) sides of the bridge
communication.

Run with: poetry run pytest tests/stagforge/test_bridge_integration.py -v
"""

import os
import threading
import time

import pytest

# Check for Playwright
try:
    from playwright.sync_api import sync_playwright, Page, Browser
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from uvicorn import Config, Server

from stagforge.bridge import EditorBridge, BridgeSessionError, BridgeProtocolError


# Skip all tests if Playwright not available
pytestmark = pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright not installed")


# Test HTML page that loads the bridge client
TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Bridge Test</title>
</head>
<body>
    <div id="status">Not connected</div>
    <div id="result"></div>
    <script type="module">
        import { EditorBridgeClient } from '/static/js/bridge/EditorBridgeClient.js';

        const sessionId = 'test-session-123';

        window.bridge = new EditorBridgeClient({
            url: `ws://${location.host}/ws/editor`,
            sessionId: sessionId,
            heartbeatInterval: 500,
            reconnectDelay: 500,
        });

        // Register test handlers
        window.bridge.registerHandler('echo', (params) => {
            return { echoed: params.message };
        });

        window.bridge.registerHandler('add', (params) => {
            return { sum: params.a + params.b };
        });

        window.bridge.registerHandler('getTimestamp', () => {
            return { timestamp: Date.now() };
        });

        window.bridge.registerHandler('throwError', () => {
            throw new Error('Intentional test error');
        });

        window.bridge.registerHandler('asyncHandler', async (params) => {
            await new Promise(resolve => setTimeout(resolve, 100));
            return { async: true, value: params.value * 2 };
        });

        // Track received events
        window.receivedEvents = [];

        window.bridge.addEventListener('connected', () => {
            document.getElementById('status').textContent = 'Connected';
            console.log('Bridge connected');
        });

        window.bridge.addEventListener('disconnected', () => {
            document.getElementById('status').textContent = 'Disconnected';
            console.log('Bridge disconnected');
        });

        // Function to emit an event (callable from Playwright)
        window.emitTestEvent = (eventName, data) => {
            window.bridge.emit(eventName, data);
        };

        // Function to get connection state
        window.getBridgeState = () => {
            return {
                isConnected: window.bridge.isConnected,
                state: window.bridge.state,
                sessionId: window.bridge.sessionId,
            };
        };

        // Connect
        window.bridge.connect().then(() => {
            console.log('Connection established');
        }).catch((err) => {
            console.error('Connection failed:', err);
            document.getElementById('status').textContent = 'Connection failed: ' + err.message;
        });
    </script>
</body>
</html>
"""


class TestServer:
    """Test server with bridge endpoint."""

    def __init__(self, port: int = 8766):
        self.port = port
        self.bridge = EditorBridge(
            session_timeout=30.0,
            heartbeat_interval=0.5,
            response_timeout=10.0,
        )
        self.received_events = []
        self.app = self._create_app()
        self.server = None
        self.thread = None

    def _create_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/")
        async def index():
            return HTMLResponse(TEST_HTML)

        @app.websocket("/ws/editor/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            # Set up event handler to capture events
            def on_event(event: str, data: dict):
                self.received_events.append({"event": event, "data": data})

            # Get or create session and set event handler
            session = self.bridge.get_or_create_session(session_id)
            session.on_event = on_event

            await self.bridge.websocket_endpoint(websocket, session_id)

        # Mount static files for the JS bridge client
        static_dir = os.path.join(os.path.dirname(__file__), '../../stagforge/frontend')
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        return app

    def start(self):
        """Start the test server in a background thread."""
        self.bridge.start()

        config = Config(
            app=self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
        )
        self.server = Server(config)

        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()

        # Wait for server to start
        time.sleep(0.5)

    def stop(self):
        """Stop the test server."""
        if self.server:
            self.server.should_exit = True
        self.bridge.stop()
        if self.thread:
            self.thread.join(timeout=2.0)


@pytest.fixture(scope="module")
def test_server():
    """Create and start a test server."""
    server = TestServer(port=8766)
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="module")
def playwright_browser():
    """Create a Playwright browser instance."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(playwright_browser):
    """Create a new page for each test."""
    context = playwright_browser.new_context()
    page = context.new_page()
    yield page
    page.close()
    context.close()


class TestBridgeConnection:
    """Test WebSocket bridge connection."""

    def test_client_connects(self, test_server, page):
        """Test that the JavaScript client connects to the server."""
        page.goto(f"http://127.0.0.1:{test_server.port}/")

        # Wait for connection
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        # Verify status
        status = page.locator("#status").text_content()
        assert status == "Connected"

        # Verify bridge state
        state = page.evaluate("window.getBridgeState()")
        assert state["isConnected"] is True
        assert state["state"] == "connected"
        assert state["sessionId"] == "test-session-123"

    def test_session_created_on_server(self, test_server, page):
        """Test that a session is created on the server when client connects."""
        page.goto(f"http://127.0.0.1:{test_server.port}/")
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        # Check server-side session
        session = test_server.bridge.get_session("test-session-123")
        assert session is not None
        assert session.is_connected is True


class TestPythonToJavaScript:
    """Test Python calling JavaScript methods."""

    def test_call_echo(self, test_server, page):
        """Test calling a simple echo handler."""
        page.goto(f"http://127.0.0.1:{test_server.port}/")
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        # Call from Python
        result = test_server.bridge.call(
            "test-session-123",
            "echo",
            {"message": "Hello from Python!"},
        )

        assert result == {"echoed": "Hello from Python!"}

    def test_call_add(self, test_server, page):
        """Test calling a handler that performs computation."""
        page.goto(f"http://127.0.0.1:{test_server.port}/")
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        result = test_server.bridge.call(
            "test-session-123",
            "add",
            {"a": 5, "b": 7},
        )

        assert result == {"sum": 12}

    def test_call_async_handler(self, test_server, page):
        """Test calling an async handler."""
        page.goto(f"http://127.0.0.1:{test_server.port}/")
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        result = test_server.bridge.call(
            "test-session-123",
            "asyncHandler",
            {"value": 21},
        )

        assert result == {"async": True, "value": 42}

    def test_call_handler_that_throws(self, test_server, page):
        """Test that handler errors are propagated."""
        page.goto(f"http://127.0.0.1:{test_server.port}/")
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        with pytest.raises(BridgeProtocolError) as exc_info:
            test_server.bridge.call("test-session-123", "throwError", {})

        assert "Intentional test error" in str(exc_info.value)

    def test_call_unknown_method(self, test_server, page):
        """Test calling an unregistered method."""
        page.goto(f"http://127.0.0.1:{test_server.port}/")
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        with pytest.raises(BridgeProtocolError) as exc_info:
            test_server.bridge.call("test-session-123", "nonexistent", {})

        assert "not found" in str(exc_info.value).lower()

    def test_fire_and_forget(self, test_server, page):
        """Test fire() which doesn't wait for response."""
        page.goto(f"http://127.0.0.1:{test_server.port}/")
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        # fire() should not block or raise
        test_server.bridge.fire("test-session-123", "echo", {"message": "fire test"})

        # Give it a moment to process
        time.sleep(0.1)


class TestJavaScriptToPython:
    """Test JavaScript sending events to Python."""

    def test_emit_event(self, test_server, page):
        """Test that JS can emit events that Python receives."""
        test_server.received_events.clear()

        page.goto(f"http://127.0.0.1:{test_server.port}/")
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        # Emit event from JavaScript
        page.evaluate("window.emitTestEvent('test-event', { foo: 'bar', num: 42 })")

        # Wait for event to arrive
        time.sleep(0.2)

        assert len(test_server.received_events) >= 1
        event = test_server.received_events[-1]
        assert event["event"] == "test-event"
        assert event["data"] == {"foo": "bar", "num": 42}

    def test_emit_multiple_events(self, test_server, page):
        """Test emitting multiple events."""
        test_server.received_events.clear()

        page.goto(f"http://127.0.0.1:{test_server.port}/")
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        # Emit multiple events
        for i in range(5):
            page.evaluate(f"window.emitTestEvent('multi-event', {{ index: {i} }})")

        # Wait for events to arrive
        time.sleep(0.3)

        multi_events = [e for e in test_server.received_events if e["event"] == "multi-event"]
        assert len(multi_events) == 5

        indices = [e["data"]["index"] for e in multi_events]
        assert indices == [0, 1, 2, 3, 4]


class TestHeartbeat:
    """Test heartbeat mechanism."""

    def test_heartbeat_keeps_session_alive(self, test_server, page):
        """Test that heartbeats keep the session alive."""
        page.goto(f"http://127.0.0.1:{test_server.port}/")
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        session = test_server.bridge.get_session("test-session-123")
        initial_heartbeat = session.last_heartbeat

        # Wait for heartbeats
        time.sleep(1.5)

        # Heartbeat should have been updated
        assert session.last_heartbeat > initial_heartbeat


class TestDisconnection:
    """Test disconnection handling."""

    def test_call_to_disconnected_session(self, test_server):
        """Test calling a session that doesn't exist."""
        with pytest.raises(BridgeSessionError):
            test_server.bridge.call("nonexistent-session", "echo", {"message": "test"})


class TestConcurrency:
    """Test concurrent calls."""

    def test_multiple_concurrent_calls(self, test_server, page):
        """Test making multiple calls concurrently."""
        page.goto(f"http://127.0.0.1:{test_server.port}/")
        page.wait_for_function("window.bridge && window.bridge.isConnected", timeout=5000)

        results = []
        errors = []

        def make_call(value):
            try:
                result = test_server.bridge.call(
                    "test-session-123",
                    "add",
                    {"a": value, "b": value},
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Launch concurrent calls from threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_call, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10

        # Verify results
        sums = sorted([r["sum"] for r in results])
        expected = [i * 2 for i in range(10)]
        assert sums == expected
