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
        assert isinstance(data, list)
        # Should have at least the skimage samples
        assert len(data) > 0

    def test_list_source_images(self, api_client: httpx.Client):
        """Can list images from a source."""
        # First get available sources
        sources_resp = api_client.get("/images/sources")
        sources = sources_resp.json()
        assert len(sources) > 0

        # Get images from first source
        source_id = sources[0]["id"]
        response = api_client.get(f"/images/{source_id}")
        assert response.status_code == 200
        images = response.json()
        assert isinstance(images, list)


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
            "/sessions/nonexistent-id/tools/brush/execute",
            json={"action": "stroke", "params": {}},
        )
        assert response.status_code == 404

    def test_execute_command_no_session(self, api_client: httpx.Client):
        """Command execution fails gracefully with no session."""
        response = api_client.post(
            "/sessions/nonexistent-id/command",
            json={"command": "undo", "params": {}},
        )
        assert response.status_code == 404
