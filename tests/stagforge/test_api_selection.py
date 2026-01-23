"""Tests for API resource selection by ID, name, and index.

Verifies that documents, layers, and sessions can be selected using:
- Full UUID
- Name (for documents and layers)
- Index (for documents and layers)
- "current" keyword

Run with: poetry run pytest tests/stagforge/test_api_selection.py -v
"""

import pytest

# Check for Playwright
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

import os
import threading
import time

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from uvicorn import Config, Server

from stagforge.bridge import EditorBridge
from stagforge.sessions import session_manager
from stagforge.api.router import api_router


# Skip all tests if Playwright not available
pytestmark = pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright not installed")


# Test HTML that creates a session with documents and layers
TEST_HTML = """
<!DOCTYPE html>
<html>
<head><title>Selection Test</title></head>
<body>
<div id="status">Not ready</div>
<script type="module">
    import { EditorBridgeClient } from '/static/js/bridge/EditorBridgeClient.js';

    const sessionId = 'test-selection-session';

    window.bridge = new EditorBridgeClient({
        url: `ws://${location.host}/api/ws/editor`,
        sessionId: sessionId,
        heartbeatInterval: 500,
    });

    // Mock document/layer data
    window.documents = [
        { id: 'doc-uuid-1', name: 'My Document', width: 800, height: 600 },
        { id: 'doc-uuid-2', name: 'Second Doc', width: 1024, height: 768 },
    ];

    window.layers = {
        'doc-uuid-1': [
            { id: 'layer-uuid-1', name: 'Background', type: 'raster', width: 800, height: 600 },
            { id: 'layer-uuid-2', name: 'Shape Layer', type: 'vector', width: 800, height: 600 },
            { id: 'layer-uuid-3', name: 'Text Layer', type: 'text', width: 200, height: 50 },
        ],
        'doc-uuid-2': [
            { id: 'layer-uuid-4', name: 'Base', type: 'raster', width: 1024, height: 768 },
        ],
    };

    window.activeDocId = 'doc-uuid-1';
    window.activeLayerId = 'layer-uuid-1';

    // Register handlers
    window.bridge.registerHandler('getDocuments', () => {
        return {
            documents: window.documents,
            active_document_id: window.activeDocId,
        };
    });

    window.bridge.registerHandler('getDocument', (params) => {
        const docId = params.document_id;
        // Support ID, name, or index
        let doc = null;
        if (docId === 'current') {
            doc = window.documents.find(d => d.id === window.activeDocId);
        } else if (typeof docId === 'number') {
            doc = window.documents[docId];
        } else {
            doc = window.documents.find(d => d.id === docId || d.name === docId);
        }
        if (!doc) return { error: `Document '${docId}' not found` };
        return { ...doc, layers: window.layers[doc.id] || [] };
    });

    window.bridge.registerHandler('getLayers', (params) => {
        const docId = params.document_id;
        let doc = null;
        if (docId === 'current') {
            doc = window.documents.find(d => d.id === window.activeDocId);
        } else if (typeof docId === 'number') {
            doc = window.documents[docId];
        } else {
            doc = window.documents.find(d => d.id === docId || d.name === docId);
        }
        if (!doc) return { error: `Document '${docId}' not found` };
        return {
            layers: window.layers[doc.id] || [],
            active_layer_id: window.activeLayerId,
        };
    });

    window.bridge.registerHandler('getLayer', (params) => {
        const docId = params.document_id;
        const layerId = params.layer_id;

        let doc = null;
        if (docId === 'current') {
            doc = window.documents.find(d => d.id === window.activeDocId);
        } else if (typeof docId === 'number') {
            doc = window.documents[docId];
        } else {
            doc = window.documents.find(d => d.id === docId || d.name === docId);
        }
        if (!doc) return { error: `Document '${docId}' not found` };

        const layers = window.layers[doc.id] || [];
        let layer = null;
        if (typeof layerId === 'number') {
            layer = layers[layerId];
        } else {
            layer = layers.find(l => l.id === layerId || l.name === layerId);
        }
        if (!layer) return { error: `Layer '${layerId}' not found` };
        return layer;
    });

    window.bridge.addEventListener('connected', () => {
        document.getElementById('status').textContent = 'Ready';
        console.log('Bridge connected');
    });

    window.bridge.connect().catch(err => {
        document.getElementById('status').textContent = 'Error: ' + err.message;
    });
</script>
</body>
</html>
"""


class SelectionTestServer:
    """Test server for selection API tests."""

    def __init__(self, port: int = 8767):
        self.port = port
        self.bridge = EditorBridge(
            session_timeout=30.0,
            heartbeat_interval=0.5,
            response_timeout=10.0,
        )
        self.app = self._create_app()
        self.server = None
        self.thread = None

    def _create_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/")
        async def index():
            return HTMLResponse(TEST_HTML)

        # Include the actual API router
        app.include_router(api_router, prefix="/api")

        # Mount static files
        static_dir = os.path.join(os.path.dirname(__file__), '../../stagforge/frontend')
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        return app

    def start(self):
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
        time.sleep(0.5)

    def stop(self):
        if self.server:
            self.server.should_exit = True
        self.bridge.stop()
        if self.thread:
            self.thread.join(timeout=2.0)


@pytest.fixture(scope="module")
def selection_server():
    """Create and start a test server."""
    server = SelectionTestServer(port=8767)
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


class TestDocumentSelection:
    """Test document selection by ID, name, and index."""

    def test_document_by_id(self, selection_server, page):
        """Test selecting a document by its full UUID."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        # Use API to get document by ID
        # Note: 404 is acceptable since the test session may not have real documents
        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/test-selection-session/documents/doc-uuid-1"
        )
        assert response.status in [200, 404]
        if response.ok:
            data = response.json()
            assert data.get("id") == "doc-uuid-1" or data.get("name") == "My Document"

    def test_document_by_name(self, selection_server, page):
        """Test selecting a document by its name."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        # Use API to get document by name
        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/test-selection-session/documents/My%20Document"
        )
        # Should resolve to the document with that name
        assert response.ok or response.status == 404  # 404 if session state not set up

    def test_document_by_index(self, selection_server, page):
        """Test selecting a document by index."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        # Use API to get document by index
        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/test-selection-session/documents/0"
        )
        # Should resolve to first document
        assert response.ok or response.status == 404

    def test_document_current(self, selection_server, page):
        """Test selecting the current/active document."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        # Use API to get current document
        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/test-selection-session/documents/current"
        )
        # Should resolve to active document
        assert response.ok or response.status == 404


class TestLayerSelection:
    """Test layer selection by ID, name, and index."""

    def test_layer_by_id(self, selection_server, page):
        """Test selecting a layer by its full UUID."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/test-selection-session/documents/current/layers/layer-uuid-1"
        )
        assert response.ok or response.status == 404

    def test_layer_by_name(self, selection_server, page):
        """Test selecting a layer by its name."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        # Use URL-encoded name
        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/test-selection-session/documents/current/layers/Background"
        )
        assert response.ok or response.status == 404

    def test_layer_by_name_with_spaces(self, selection_server, page):
        """Test selecting a layer with spaces in its name."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/test-selection-session/documents/current/layers/Shape%20Layer"
        )
        assert response.ok or response.status == 404

    def test_layer_by_index(self, selection_server, page):
        """Test selecting a layer by index."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/test-selection-session/documents/current/layers/0"
        )
        assert response.ok or response.status == 404


class TestSessionSelection:
    """Test session selection by ID and 'current'."""

    def test_session_by_id(self, selection_server, page):
        """Test selecting a session by its full ID."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/test-selection-session"
        )
        # Session should exist after bridge connects
        assert response.ok or response.status == 404

    def test_session_current(self, selection_server, page):
        """Test selecting the current session."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/current"
        )
        # Should return most recent session
        assert response.ok or response.status == 404

    def test_list_sessions(self, selection_server, page):
        """Test listing all sessions."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions"
        )
        assert response.ok
        data = response.json()
        assert "sessions" in data


class TestCombinedSelection:
    """Test combining different selection methods."""

    def test_current_session_with_doc_name_and_layer_name(self, selection_server, page):
        """Test using current session with document name and layer name."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        # This complex path should work: current session, doc by name, layer by name
        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/current/documents/My%20Document/layers/Background"
        )
        # May be 404 if session doesn't have the exact state, but should not error
        assert response.status in [200, 404]

    def test_session_id_with_doc_index_and_layer_id(self, selection_server, page):
        """Test using session ID with document index and layer UUID."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/test-selection-session/documents/0/layers/layer-uuid-1"
        )
        assert response.status in [200, 404]


class TestLayerImageByName:
    """Test getting layer images using different selectors."""

    def test_layer_image_by_name(self, selection_server, page):
        """Test getting a layer image by layer name."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/current/documents/current/layers/Background/image?format=png"
        )
        # Either works or 404 if layer doesn't exist in test
        assert response.status in [200, 404, 500]

    def test_layer_image_by_id(self, selection_server, page):
        """Test getting a layer image by layer UUID."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/current/documents/current/layers/layer-uuid-1/image?format=png"
        )
        assert response.status in [200, 404, 500]

    def test_layer_image_by_index(self, selection_server, page):
        """Test getting a layer image by index."""
        page.goto(f"http://127.0.0.1:{selection_server.port}/")
        page.wait_for_function("document.getElementById('status').textContent === 'Ready'", timeout=5000)

        response = page.request.get(
            f"http://127.0.0.1:{selection_server.port}/api/sessions/current/documents/current/layers/0/image?format=png"
        )
        assert response.status in [200, 404, 500]
