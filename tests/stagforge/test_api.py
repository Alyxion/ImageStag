"""API endpoint tests."""

import pytest
import httpx


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, api_client: httpx.Client):
        """Health endpoint returns OK status."""
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestFiltersEndpoint:
    """Tests for the filters API."""

    def test_list_filters(self, api_client: httpx.Client):
        """List filters returns available filters."""
        response = api_client.get("/filters")
        assert response.status_code == 200
        data = response.json()
        assert "filters" in data
        # Should have at least some built-in filters
        assert len(data["filters"]) > 0

    def test_filter_has_required_fields(self, api_client: httpx.Client):
        """Each filter has required metadata fields."""
        response = api_client.get("/filters")
        data = response.json()

        for filter_info in data["filters"]:
            assert "id" in filter_info
            assert "name" in filter_info
            assert "category" in filter_info


class TestImagesEndpoint:
    """Tests for the images/sources API."""

    def test_list_sources(self, api_client: httpx.Client):
        """List sources returns available image sources."""
        response = api_client.get("/images/sources")
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)
        # Should have at least the skimage samples
        assert len(data["sources"]) > 0

    def test_list_source_images(self, api_client: httpx.Client):
        """Can list images from a source."""
        # First get available sources
        sources_resp = api_client.get("/images/sources")
        data = sources_resp.json()
        sources = data["sources"]
        assert len(sources) > 0

        # Get images from first source
        source_id = sources[0]["id"]
        response = api_client.get(f"/images/{source_id}")
        assert response.status_code == 200
        result = response.json()
        assert "images" in result
        assert isinstance(result["images"], list)


class TestSessionsEndpoint:
    """Tests for the sessions API.

    Note: Most session operations require an active browser session
    with the JavaScript editor running. These tests verify the API
    structure and error handling without requiring a browser.
    """

    def test_list_sessions_empty(self, api_client: httpx.Client):
        """List sessions returns empty list when no sessions."""
        response = api_client.get("/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_get_nonexistent_session(self, api_client: httpx.Client):
        """Getting a nonexistent session returns 404."""
        response = api_client.get("/sessions/nonexistent-id")
        assert response.status_code == 404

    def test_execute_tool_no_session(self, api_client: httpx.Client):
        """Tool execution fails gracefully with no session."""
        response = api_client.post(
            "/sessions/nonexistent-id/documents/current/tools/brush/execute",
            json={"action": "stroke", "params": {}},
        )
        assert response.status_code == 404

    def test_execute_command_no_session(self, api_client: httpx.Client):
        """Command execution fails gracefully with no session."""
        response = api_client.post(
            "/sessions/nonexistent-id/documents/current/command",
            json={"command": "undo", "params": {}},
        )
        assert response.status_code == 404

    def test_heartbeat_no_session(self, api_client: httpx.Client):
        """Heartbeat on nonexistent session returns 404."""
        response = api_client.post("/sessions/nonexistent-id/heartbeat")
        assert response.status_code == 404

    def test_heartbeat_current_no_session(self, api_client: httpx.Client):
        """Heartbeat with 'current' fails when no sessions exist."""
        response = api_client.post("/sessions/current/heartbeat")
        assert response.status_code == 404


class TestImageEndpoint:
    """Tests for the image retrieval API.

    Note: These tests verify error handling and parameter validation.
    Full image retrieval requires an active browser session.
    """

    def test_get_image_no_session(self, api_client: httpx.Client):
        """Image retrieval fails gracefully with no session."""
        response = api_client.get("/sessions/nonexistent-id/documents/current/image")
        assert response.status_code == 404

    def test_get_image_invalid_format(self, api_client: httpx.Client):
        """Invalid format parameter returns 400."""
        response = api_client.get(
            "/sessions/current/documents/current/image?format=invalid"
        )
        # Should be 400 for invalid format (if session exists) or 404 (no session)
        assert response.status_code in (400, 404)

    def test_get_layer_image_no_session(self, api_client: httpx.Client):
        """Layer image retrieval fails gracefully with no session."""
        response = api_client.get(
            "/sessions/nonexistent-id/documents/current/layers/0/image"
        )
        assert response.status_code == 404

    def test_get_layer_image_invalid_format(self, api_client: httpx.Client):
        """Invalid layer format parameter returns 400."""
        response = api_client.get(
            "/sessions/current/documents/current/layers/0/image?format=invalid"
        )
        # Should be 400 for invalid format (if session exists) or 404 (no session)
        assert response.status_code in (400, 404)


class TestUploadEndpoint:
    """Tests for the upload/data cache API."""

    def test_upload_stats(self, api_client: httpx.Client):
        """Upload stats endpoint returns cache statistics."""
        response = api_client.get("/upload/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_bytes" in data
        assert "max_bytes" in data
        assert "entry_count" in data
        assert "pending_count" in data
        assert "usage_percent" in data

    def test_upload_without_request_fails(self, api_client: httpx.Client):
        """Upload without pending request fails."""
        response = api_client.post(
            "/upload/nonexistent-request-id",
            content=b"test data",
            headers={"Content-Type": "image/webp"},
        )
        assert response.status_code == 400
        data = response.json()
        assert "not found" in data.get("detail", "").lower()

    def test_upload_empty_body_fails(self, api_client: httpx.Client):
        """Upload with empty body fails."""
        response = api_client.post(
            "/upload/some-request-id",
            content=b"",
            headers={"Content-Type": "image/webp"},
        )
        assert response.status_code == 400


class TestToolsEndpoint:
    """Tests for the tools listing API."""

    def test_list_tools(self, api_client: httpx.Client):
        """List tools returns available tools."""
        response = api_client.get("/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        # Tools is a dict with tool_id -> tool_info
        assert isinstance(data["tools"], dict)
        assert len(data["tools"]) > 0

    def test_tool_has_required_fields(self, api_client: httpx.Client):
        """Each tool has required metadata fields."""
        response = api_client.get("/tools")
        data = response.json()

        for tool_id, tool_info in data["tools"].items():
            assert isinstance(tool_id, str)
            assert "name" in tool_info
            assert "actions" in tool_info


class TestEffectsEndpoint:
    """Tests for the effects listing API."""

    def test_list_effects(self, api_client: httpx.Client):
        """List effects returns available effect types."""
        response = api_client.get("/effects")
        assert response.status_code == 200
        data = response.json()
        assert "effects" in data
        # Effects is a dict with effect_type -> effect_info
        assert isinstance(data["effects"], dict)
        assert len(data["effects"]) > 0

    def test_effect_has_required_fields(self, api_client: httpx.Client):
        """Each effect type has required metadata fields."""
        response = api_client.get("/effects")
        data = response.json()

        for effect_type, effect_info in data["effects"].items():
            assert isinstance(effect_type, str)
            assert "name" in effect_info
            assert "params" in effect_info


class TestLayerContentEndpoint:
    """Tests for the layer content API.

    These tests verify format validation and error handling.
    Full content retrieval requires an active browser session.
    """

    def test_get_layer_image_valid_formats(self, api_client: httpx.Client):
        """Valid format parameters are accepted (404 without session, not 400)."""
        valid_formats = ["webp", "avif", "png", "svg", "json"]
        for fmt in valid_formats:
            response = api_client.get(
                f"/sessions/current/documents/current/layers/0/image?format={fmt}"
            )
            # Should be 404 (no session) not 400 (invalid format)
            assert response.status_code == 404, f"Format {fmt} should be valid"

    def test_get_layer_image_invalid_format_returns_400(self, api_client: httpx.Client):
        """Invalid format parameter returns 400."""
        response = api_client.get(
            "/sessions/current/documents/current/layers/0/image?format=gif"
        )
        # Should be 400 for invalid format
        assert response.status_code == 400
        data = response.json()
        assert "invalid format" in data.get("detail", "").lower()

    def test_get_layer_image_no_session(self, api_client: httpx.Client):
        """Layer image retrieval fails gracefully with no session."""
        response = api_client.get(
            "/sessions/nonexistent-id/documents/current/layers/0/image"
        )
        assert response.status_code == 404

    def test_get_layer_by_index(self, api_client: httpx.Client):
        """Layer can be specified by index."""
        response = api_client.get(
            "/sessions/current/documents/current/layers/0/image"
        )
        # Should be 404 (no session) - validates URL parsing works
        assert response.status_code == 404

    def test_get_layer_by_name(self, api_client: httpx.Client):
        """Layer can be specified by name."""
        response = api_client.get(
            "/sessions/current/documents/current/layers/Background/image"
        )
        # Should be 404 (no session) - validates URL parsing works
        assert response.status_code == 404

    def test_get_layer_image_with_background(self, api_client: httpx.Client):
        """Background color parameter is accepted."""
        response = api_client.get(
            "/sessions/current/documents/current/layers/0/image?format=png&bg=%23FFFFFF"
        )
        # Should be 404 (no session) - bg param doesn't cause errors
        assert response.status_code == 404


class TestBrowserStorageEndpoint:
    """Tests for the browser storage (OPFS) API.

    These tests verify error handling and parameter validation.
    Full storage operations require an active browser session with OPFS support.
    """

    def test_list_stored_documents_no_session(self, api_client: httpx.Client):
        """List stored documents fails gracefully with no session."""
        response = api_client.get("/sessions/nonexistent-id/storage/documents")
        assert response.status_code == 404

    def test_list_stored_documents_current_no_session(self, api_client: httpx.Client):
        """List stored documents with 'current' fails when no sessions exist."""
        response = api_client.get("/sessions/current/storage/documents")
        assert response.status_code == 404

    def test_clear_stored_documents_no_session(self, api_client: httpx.Client):
        """Clear stored documents fails gracefully with no session."""
        response = api_client.delete("/sessions/nonexistent-id/storage/documents")
        assert response.status_code == 404

    def test_delete_stored_document_no_session(self, api_client: httpx.Client):
        """Delete specific stored document fails gracefully with no session."""
        response = api_client.delete(
            "/sessions/nonexistent-id/storage/documents/some-doc-id"
        )
        assert response.status_code == 404

    def test_delete_stored_document_current_no_session(self, api_client: httpx.Client):
        """Delete stored document with 'current' fails when no sessions exist."""
        response = api_client.delete(
            "/sessions/current/storage/documents/some-doc-id"
        )
        assert response.status_code == 404


class TestBrowserEndpoint:
    """Tests for the document browser UI."""

    def test_browser_returns_html(self, api_client: httpx.Client):
        """Browser endpoint returns HTML page."""
        response = api_client.get("/browse")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "Stagforge Browser" in response.text

    def test_browser_with_trailing_slash(self, api_client: httpx.Client):
        """Browser endpoint works with trailing slash."""
        response = api_client.get("/browse/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_browser_has_required_elements(self, api_client: httpx.Client):
        """Browser page contains required UI elements."""
        response = api_client.get("/browse")
        html = response.text
        # Check for key UI sections
        assert "Sessions" in html
        assert "Documents" in html
        assert "layers" in html.lower()
        # Check that JS and CSS are linked with absolute paths
        assert "/api/browse/app.js" in html
        assert "/api/browse/style.css" in html

    def test_browser_serves_css(self, api_client: httpx.Client):
        """Browser serves CSS file."""
        response = api_client.get("/browse/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")
        assert ".header" in response.text

    def test_browser_serves_js(self, api_client: httpx.Client):
        """Browser serves JavaScript file."""
        response = api_client.get("/browse/app.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")
        assert "loadSessions" in response.text
        assert "/api" in response.text
