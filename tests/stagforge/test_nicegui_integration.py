"""Unit tests for NiceGUI integration components.

These tests verify the StagforgeEditor component configuration
without requiring a running server or browser.
"""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np


class TestStagforgeEditorConfig:
    """Test StagforgeEditor URL generation and configuration."""

    @pytest.fixture
    def mock_element(self):
        """Mock the NiceGUI Element base class."""
        with patch('stagforge.nicegui.editor.Element') as mock:
            mock.return_value = MagicMock()
            yield mock

    def test_default_config(self, mock_element):
        """Test editor with default configuration."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor()

        # Check URL was set
        assert 'src' in editor._props
        url = editor._props['src']

        # Default params should be present
        assert 'session_id=' in url
        assert 'width=800' in url
        assert 'height=600' in url

        # No visibility params when all are true (defaults)
        assert 'show_menu=false' not in url
        assert 'show_navigator=false' not in url

    def test_custom_dimensions(self, mock_element):
        """Test editor with custom iframe and document dimensions."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(
            width=1200,
            height=800,
            doc_width=512,
            doc_height=512,
        )

        url = editor._props['src']
        # Document dimensions should be in URL
        assert 'width=512' in url
        assert 'height=512' in url

        # Iframe dimensions in style
        assert 'width:1200px' in editor._props['style']
        assert 'height:800px' in editor._props['style']

    def test_isolated_mode(self, mock_element):
        """Test editor with isolated mode enabled."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(isolated=True)

        url = editor._props['src']
        assert 'isolated=true' in url

    def test_empty_mode_with_initial_image(self, mock_element):
        """Test that initial_image triggers empty mode."""
        from stagforge.nicegui.editor import StagforgeEditor

        # Mock numpy array
        fake_image = np.zeros((100, 100, 3), dtype=np.uint8)

        editor = StagforgeEditor(initial_image=fake_image)

        url = editor._props['src']
        assert 'empty=true' in url

    def test_hide_menu(self, mock_element):
        """Test hiding the menu bar."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(show_menu=False)

        url = editor._props['src']
        assert 'show_menu=false' in url

    def test_hide_navigator(self, mock_element):
        """Test hiding the navigator panel."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(show_navigator=False)

        url = editor._props['src']
        assert 'show_navigator=false' in url

    def test_hide_layers(self, mock_element):
        """Test hiding the layers panel."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(show_layers=False)

        url = editor._props['src']
        assert 'show_layers=false' in url

    def test_hide_tool_properties(self, mock_element):
        """Test hiding tool properties/ribbon."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(show_tool_properties=False)

        url = editor._props['src']
        assert 'show_tool_properties=false' in url

    def test_hide_bottom_bar(self, mock_element):
        """Test hiding the bottom status bar."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(show_bottom_bar=False)

        url = editor._props['src']
        assert 'show_bottom_bar=false' in url

    def test_hide_history(self, mock_element):
        """Test hiding the history panel."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(show_history=False)

        url = editor._props['src']
        assert 'show_history=false' in url

    def test_hide_toolbar(self, mock_element):
        """Test hiding the tools panel."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(show_toolbar=False)

        url = editor._props['src']
        assert 'show_toolbar=false' in url

    def test_hide_multiple_panels(self, mock_element):
        """Test hiding multiple panels at once."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(
            show_menu=False,
            show_navigator=False,
            show_layers=False,
            show_history=False,
        )

        url = editor._props['src']
        assert 'show_menu=false' in url
        assert 'show_navigator=false' in url
        assert 'show_layers=false' in url
        assert 'show_history=false' in url

    def test_visible_tool_groups(self, mock_element):
        """Test specifying visible tool groups."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(
            visible_tool_groups=['brush', 'eraser', 'fill']
        )

        url = editor._props['src']
        assert 'visible_tool_groups=brush,eraser,fill' in url

    def test_hidden_tool_groups(self, mock_element):
        """Test specifying hidden tool groups."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(
            hidden_tool_groups=['crop', 'text']
        )

        url = editor._props['src']
        assert 'hidden_tool_groups=crop,text' in url

    def test_custom_server_url(self, mock_element):
        """Test with custom server URL."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(server_url='http://localhost:9000')

        url = editor._props['src']
        assert url.startswith('http://localhost:9000/editor?')

    def test_session_id_generated(self, mock_element):
        """Test that unique session IDs are generated."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor1 = StagforgeEditor()
        editor2 = StagforgeEditor()

        assert editor1.session_id != editor2.session_id
        assert len(editor1.session_id) == 36  # UUID format


class TestStagforgeEditorToolGroups:
    """Test tool group constants and validation."""

    def test_tool_groups_defined(self):
        """Test that TOOL_GROUPS constant is defined with all categories."""
        from stagforge.nicegui.editor import StagforgeEditor

        expected_groups = [
            'selection', 'freeform', 'quicksel', 'move', 'crop', 'hand',
            'brush', 'eraser', 'stamp', 'retouch', 'dodge',
            'pen', 'shapes', 'fill', 'text', 'eyedropper'
        ]

        for group in expected_groups:
            assert group in StagforgeEditor.TOOL_GROUPS, f"Missing group: {group}"

    def test_tool_groups_have_descriptions(self):
        """Test that all tool groups have non-empty descriptions."""
        from stagforge.nicegui.editor import StagforgeEditor

        for group, description in StagforgeEditor.TOOL_GROUPS.items():
            assert isinstance(description, str), f"Description for {group} is not a string"
            assert len(description) > 0, f"Description for {group} is empty"


class TestEditorTemplateParams:
    """Test that template parameters are correctly structured."""

    def test_standalone_route_params(self):
        """Test standalone.py accepts all required parameters."""
        from stagforge.standalone import create_standalone_app
        from fastapi.testclient import TestClient

        app = create_standalone_app()
        client = TestClient(app)

        # Test with all parameters
        response = client.get(
            "/?session_id=test123"
            "&isolated=true"
            "&empty=true"
            "&width=512"
            "&height=512"
            "&show_menu=false"
            "&show_navigator=false"
            "&show_layers=false"
            "&show_tool_properties=false"
            "&show_bottom_bar=false"
            "&show_history=false"
            "&show_toolbar=false"
            "&visible_tool_groups=brush,eraser"
            "&hidden_tool_groups=crop"
        )

        assert response.status_code == 200
        html = response.text

        # Verify config is in the response
        assert 'session_id' in html or 'sessionId' in html
        assert 'isolated' in html

    def test_standalone_route_defaults(self):
        """Test standalone.py works with default parameters."""
        from stagforge.standalone import create_standalone_app
        from fastapi.testclient import TestClient

        app = create_standalone_app()
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        html = response.text

        # Should have sensible defaults
        assert 'width' in html or 'canvasWidth' in html
        assert 'height' in html or 'canvasHeight' in html


class TestToolGroupFiltering:
    """Test tool group filtering logic."""

    @pytest.fixture
    def mock_element(self):
        """Mock the NiceGUI Element base class."""
        with patch('stagforge.nicegui.editor.Element') as mock:
            mock.return_value = MagicMock()
            yield mock

    def test_empty_visible_groups_shows_all(self, mock_element):
        """Test that None visible_tool_groups shows all tools."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(visible_tool_groups=None)

        url = editor._props['src']
        # Should NOT have visible_tool_groups param when None
        assert 'visible_tool_groups=' not in url

    def test_empty_hidden_groups_list(self, mock_element):
        """Test that empty hidden_tool_groups list doesn't add param."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(hidden_tool_groups=[])

        url = editor._props['src']
        # Should NOT have hidden_tool_groups param when empty
        assert 'hidden_tool_groups=' not in url

    def test_drawing_preset(self, mock_element):
        """Test a typical drawing-only configuration."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(
            visible_tool_groups=['brush', 'eraser', 'fill', 'eyedropper']
        )

        url = editor._props['src']
        assert 'brush' in url
        assert 'eraser' in url
        assert 'fill' in url
        assert 'eyedropper' in url

    def test_minimal_ui(self, mock_element):
        """Test minimal UI configuration (no panels, only drawing tools)."""
        from stagforge.nicegui.editor import StagforgeEditor

        editor = StagforgeEditor(
            show_menu=False,
            show_navigator=False,
            show_layers=False,
            show_tool_properties=False,
            show_history=False,
            show_bottom_bar=False,
            visible_tool_groups=['brush', 'eraser'],
        )

        url = editor._props['src']

        # All panels hidden
        assert 'show_menu=false' in url
        assert 'show_navigator=false' in url
        assert 'show_layers=false' in url
        assert 'show_tool_properties=false' in url
        assert 'show_history=false' in url
        assert 'show_bottom_bar=false' in url

        # Only brush and eraser tools
        assert 'visible_tool_groups=brush,eraser' in url
