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
