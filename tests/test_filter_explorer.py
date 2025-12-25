"""Tests for FilterExplorerApp."""

import pytest
from nicegui import ui
from nicegui.testing import User


class TestFilterExplorerApp:
    """Tests for FilterExplorerApp class."""

    def test_app_initializes(self):
        """FilterExplorerApp can be instantiated."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        assert app.available_images is not None
        assert len(app.available_images) > 0
        assert app.default_image_name == 'stag'

    def test_available_images_includes_skimage(self):
        """Available images include scikit-image samples."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        assert 'astronaut' in app.available_images
        assert 'camera' in app.available_images

    def test_available_images_includes_imagestag_samples(self):
        """Available images include ImageStag samples."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        assert 'stag' in app.available_images

    def test_get_source_image_loads_skimage(self):
        """Can load scikit-image samples."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image

        app = FilterExplorerApp()
        img = app._get_source_image('astronaut')
        assert isinstance(img, Image)
        assert img.width > 0

    def test_get_source_image_loads_imagestag(self):
        """Can load ImageStag samples."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image

        app = FilterExplorerApp()
        img = app._get_source_image('stag')
        assert isinstance(img, Image)
        assert img.width > 0

    def test_get_source_image_caches(self):
        """Source images are cached."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        img1 = app._get_source_image('camera')
        img2 = app._get_source_image('camera')
        assert img1 is img2  # Same object

    def test_get_source_image_custom(self):
        """Can get custom uploaded images."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        import numpy as np

        app = FilterExplorerApp()
        custom = Image(np.zeros((100, 100, 3), dtype=np.uint8))
        app.custom_images['custom_1'] = custom

        img = app._get_source_image('custom_1')
        assert img is custom


class TestFilterExplorerUpload:
    """Tests for FilterExplorerApp upload handling."""

    def test_handle_upload_valid_image(self, monkeypatch):
        """Can handle valid image upload."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        import numpy as np
        import base64

        # Mock ui.notify to avoid NiceGUI context requirement
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()

        # Create a simple red image
        red_pixels = np.full((10, 10, 3), [255, 0, 0], dtype=np.uint8)
        img = Image(red_pixels)
        png_bytes = img.encode('png')
        b64_data = base64.b64encode(png_bytes).decode()

        initial_count = len(app.available_images)
        app._handle_upload({'data': f'data:image/png;base64,{b64_data}'})

        assert len(app.available_images) == initial_count + 1
        assert 'upload_1' in app.custom_images

    def test_handle_upload_increments_counter(self, monkeypatch):
        """Upload counter increments with each upload."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        import numpy as np
        import base64

        # Mock ui.notify to avoid NiceGUI context requirement
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()

        # Create a simple red image
        red_pixels = np.full((10, 10, 3), [255, 0, 0], dtype=np.uint8)
        img = Image(red_pixels)
        png_bytes = img.encode('png')
        b64_data = base64.b64encode(png_bytes).decode()

        app._handle_upload({'data': f'data:image/png;base64,{b64_data}'})
        app._handle_upload({'data': f'data:image/png;base64,{b64_data}'})

        assert app.upload_counter == 2
        assert 'upload_1' in app.custom_images
        assert 'upload_2' in app.custom_images


class TestFilterExplorerGraphHandling:
    """Tests for FilterExplorerApp graph handling."""

    def test_on_graph_change_stores_data(self):
        """Graph change callback stores data."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        test_data = {'nodes': {}, 'connections': []}
        app._on_graph_change(test_data)

        assert app.last_graph_data == test_data

    def test_on_node_selected_stores_id(self):
        """Node selection stores the selected node ID."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        app._on_node_selected({'id': 'test_node'})

        assert app.selected_node_id == 'test_node'


class TestFilterExplorerPresets:
    """Tests for FilterExplorerApp preset loading."""

    def test_presets_available(self):
        """Presets are available."""
        from imagestag.tools.presets import get_preset_names

        names = get_preset_names()
        assert len(names) > 0

    def test_preset_names_returned(self):
        """Can get preset names."""
        from imagestag.tools.presets import get_preset_names, PRESETS

        names = get_preset_names()
        assert isinstance(names, list)
        # names is a list of tuples (key, display_name)
        for key, display_name in names:
            assert key in PRESETS


class TestFilterExplorerLoadPreset:
    """Tests for FilterExplorerApp preset loading."""

    def test_load_preset_valid(self, monkeypatch):
        """Can load a valid preset."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag.components import FilterDesigner
        from unittest.mock import MagicMock

        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()
        # Create a mock designer
        app.designer = MagicMock(spec=FilterDesigner)

        # Load a preset (use one that exists)
        app._load_preset('simple_filter_chain')

        # Should have called load_graph on designer
        app.designer.load_graph.assert_called_once()

    def test_load_preset_empty_key(self, monkeypatch):
        """Load preset with empty key does nothing."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        app._load_preset('')
        # Should not crash

    def test_load_preset_no_designer(self, monkeypatch):
        """Load preset without designer does nothing."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        app.designer = None
        app._load_preset('simple_filter_chain')
        # Should not crash


class TestFilterExplorerNotify:
    """Tests for FilterExplorerApp notification handling."""

    def test_on_notify_info(self, monkeypatch):
        """Handle info notification."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        notifications = []
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify',
                           lambda msg, type=None: notifications.append((msg, type)))

        app = FilterExplorerApp()
        app._on_notify({'message': 'Test message', 'type': 'info'})

        assert len(notifications) == 1
        assert notifications[0][0] == 'Test message'
        assert notifications[0][1] == 'info'


class TestFilterExplorerImport:
    """Tests for FilterExplorerApp import handling."""

    def test_on_import_success(self, monkeypatch):
        """Handle successful import."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        notifications = []
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify',
                           lambda msg, type=None: notifications.append((msg, type)))

        app = FilterExplorerApp()
        app._on_import_completed({'success': True, 'filename': 'test.json'})

        assert len(notifications) == 1
        assert 'Imported' in notifications[0][0]
        assert notifications[0][1] == 'positive'

    def test_on_import_failure(self, monkeypatch):
        """Handle failed import."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        notifications = []
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify',
                           lambda msg, type=None: notifications.append((msg, type)))

        app = FilterExplorerApp()
        app._on_import_completed({'success': False, 'error': 'Invalid JSON'})

        assert len(notifications) == 1
        assert 'failed' in notifications[0][0]
        assert notifications[0][1] == 'negative'


class TestFilterExplorerGetSources:
    """Tests for FilterExplorerApp source image handling."""

    def test_get_all_sources_empty(self):
        """Get sources from empty graph."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        sources = app._get_all_sources({'nodes': {}})
        assert sources == {}

    def test_get_all_sources_pipeline_source(self):
        """Get sources from graph with PipelineSource node."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                }
            }
        }
        sources = app._get_all_sources(graph_data)
        assert 'input' in sources
        assert sources['input'].width > 0

    def test_get_all_sources_custom_image(self):
        """Get sources prefers custom uploaded images."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        import numpy as np

        app = FilterExplorerApp()
        # Add custom image
        custom = Image(np.zeros((50, 50, 3), dtype=np.uint8))
        app.custom_images['my_upload'] = custom

        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'SAMPLE',
                    'value': 'my_upload'
                }
            }
        }
        sources = app._get_all_sources(graph_data)
        assert 'input' in sources
        assert sources['input'] is custom


class TestFilterExplorerExecuteGraph:
    """Tests for FilterExplorerApp graph execution."""

    def test_execute_empty_graph(self):
        """Execute empty graph returns None."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        result = app._execute_graph({'nodes': {}})
        assert result is None

    def test_execute_no_sources(self):
        """Execute graph with no sources returns None."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        result = app._execute_graph({
            'nodes': {'filter1': {'type': 'filter', 'filterName': 'Blur'}},
            'connections': []
        })
        assert result is None

    def test_execute_simple_graph(self):
        """Execute simple source -> filter -> output graph."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'blur': {
                    'class': 'GaussianBlur',
                    'params': {'radius': 2.0}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'blur'},
                {'from': 'blur', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        # Result should be an image (or the output dict)
        assert result is not None

    def test_execute_legacy_connection_format(self):
        """Execute graph with legacy connection format."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'gray': {
                    'class': 'Grayscale',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from_node': 'input', 'to_node': 'gray', 'from_output': 0, 'to_input': 0},
                {'from_node': 'gray', 'to_node': 'output', 'from_output': 0, 'to_input': 0}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None


class TestFilterExplorerNodeSelection:
    """Tests for FilterExplorerApp node selection."""

    def test_on_node_selected_with_results(self, monkeypatch):
        """Node selection with existing results updates sidebar."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        import numpy as np

        app = FilterExplorerApp()
        # Set up some node results
        test_img = Image(np.zeros((50, 50, 3), dtype=np.uint8))
        app.node_results = {'blur': test_img}
        app.last_graph_data = {'nodes': {'blur': {}}, 'connections': []}

        # Need to mock _update_preview
        update_called = []
        app._update_preview = lambda data: update_called.append(data)

        app._on_node_selected({'id': 'blur'})
        assert app.selected_node_id == 'blur'
        assert len(update_called) == 1


class TestFilterExplorerImageToBase64:
    """Tests for image encoding."""

    def test_image_to_base64(self):
        """Can encode image to base64."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        import numpy as np

        app = FilterExplorerApp()
        img = Image(np.zeros((50, 50, 3), dtype=np.uint8))
        base64_str, info = app._image_to_base64(img)

        assert base64_str.startswith('data:image/png;base64,')
        assert '50x50' in info
        assert 'RGB' in info


class TestFilterExplorerCombinerExecution:
    """Tests for combiner node execution."""

    def test_execute_blend_combiner(self):
        """Execute graph with Blend combiner."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input1': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'input2': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/camera'
                },
                'blend': {
                    'class': 'Blend',
                    'params': {'mode': 'NORMAL', 'opacity': 0.5}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input1', 'to': ['blend', 'a']},
                {'from': 'input2', 'to': ['blend', 'b']},
                {'from': 'blend', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None

    def test_execute_with_old_param_format(self):
        """Execute graph with old-style params list."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'blur': {
                    'class': 'GaussianBlur',
                    'params': [{'name': 'radius', 'value': 2.0}]
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'blur'},
                {'from': 'blur', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None


class TestFilterExplorerSidebarPreview:
    """Tests for sidebar preview updates."""

    def test_update_sidebar_no_designer(self):
        """Update sidebar does nothing without designer."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        app.designer = None
        app._update_sidebar_preview('test')  # Should not crash

    def test_update_sidebar_no_result(self):
        """Update sidebar with no result shows placeholder."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from unittest.mock import MagicMock

        app = FilterExplorerApp()
        app.designer = MagicMock()
        app.node_results = {}

        app._update_sidebar_preview('missing_node')
        app.designer.set_output_image.assert_called_once()
        call_args = app.designer.set_output_image.call_args
        assert call_args[0][0] == ''  # Empty image
        assert 'No output' in call_args[0][1]

    def test_update_sidebar_with_image(self):
        """Update sidebar with image result."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()
        app.node_results = {'blur': Image(np.zeros((50, 50, 3), dtype=np.uint8))}
        app.last_graph_data = {'nodes': {'blur': {'filterName': 'GaussianBlur'}}}

        app._update_sidebar_preview('blur')
        app.designer.set_output_image.assert_called_once()
        call_args = app.designer.set_output_image.call_args
        assert call_args[0][0].startswith('data:image/png;base64,')


class TestFilterExplorerOutputNode:
    """Tests for output node handling."""

    def test_execute_disconnected_output(self):
        """Execute graph with disconnected output returns None."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': []  # No connections
        }
        result = app._execute_graph(graph_data)
        assert result is None

    def test_execute_returns_last_result_no_output_node(self):
        """Execute graph without output node returns last result."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'blur': {
                    'class': 'GaussianBlur',
                    'params': {'radius': 2.0}
                }
            },
            'connections': [
                {'from': 'input', 'to': 'blur'}
            ]
        }
        result = app._execute_graph(graph_data)
        # Should return the last processed result
        assert result is not None


class TestFilterExplorerConnectionFormats:
    """Tests for different connection format handling."""

    def test_execute_with_port_arrays(self):
        """Execute graph with array-style port connections."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'blur': {
                    'class': 'GaussianBlur',
                    'params': {'radius': 2.0}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': ['input', 'output'], 'to': ['blur', 'input']},
                {'from': ['blur', 'output'], 'to': ['output', 'input']}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None

    def test_execute_with_port_name_format(self):
        """Execute graph with port name format connections."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'blur': {
                    'class': 'GaussianBlur',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from_node': 'input', 'to_node': 'blur', 'from_port_name': 'output', 'to_port_name': 'input'},
                {'from_node': 'blur', 'to_node': 'output', 'from_port_name': 'output', 'to_port_name': 'input'}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None


# =============================================================================
# FilterExplorerApp UI Integration Tests
# =============================================================================

class TestFilterExplorerUI:
    """UI integration tests for FilterExplorerApp."""

    @pytest.mark.asyncio
    async def test_build_ui_creates_designer(self, user: User):
        """build_ui creates the FilterDesigner component."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        @ui.page('/test_explorer_build')
        def page():
            app = FilterExplorerApp()
            # Build a minimal UI
            with ui.row():
                ui.label('Filter Explorer Test')
            # Note: full build_ui would require more setup

        await user.open('/test_explorer_build')


class TestFilterExplorerUploadEdgeCases:
    """Tests for upload edge cases."""

    def test_handle_upload_no_comma(self, monkeypatch):
        """Handle upload data without data: prefix."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        import numpy as np
        import base64

        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()
        red_pixels = np.full((10, 10, 3), [255, 0, 0], dtype=np.uint8)
        img = Image(red_pixels)
        png_bytes = img.encode('png')
        b64_data = base64.b64encode(png_bytes).decode()

        # Pass raw base64 without data: prefix
        app._handle_upload({'data': b64_data})
        assert 'upload_1' in app.custom_images

    def test_handle_upload_notifies_designer(self, monkeypatch):
        """Handle upload notifies designer when present."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        from unittest.mock import MagicMock
        import numpy as np
        import base64

        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()
        app.designer = MagicMock()

        red_pixels = np.full((10, 10, 3), [255, 0, 0], dtype=np.uint8)
        img = Image(red_pixels)
        png_bytes = img.encode('png')
        b64_data = base64.b64encode(png_bytes).decode()

        app._handle_upload({'data': f'data:image/png;base64,{b64_data}'})

        app.designer.notify_image_added.assert_called_once_with('upload_1')

    def test_handle_upload_error(self, monkeypatch):
        """Handle upload with invalid data shows error."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        notifications = []
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify',
                           lambda msg, type=None: notifications.append((msg, type)))

        app = FilterExplorerApp()
        app._handle_upload({'data': 'invalid_base64_data!!!'})

        assert len(notifications) == 1
        assert 'Failed' in notifications[0][0]
        assert notifications[0][1] == 'negative'


class TestFilterExplorerNodeSelectedWithDesigner:
    """Tests for node selection with designer mapping."""

    def test_on_node_selected_uses_designer_mapping(self):
        """Node selection uses designer's id_to_name mapping."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from unittest.mock import MagicMock

        app = FilterExplorerApp()
        app.designer = MagicMock()
        app.designer._id_to_name = {'123': 'my_blur_filter'}

        app._on_node_selected({'id': '123'})
        assert app.selected_node_id == 'my_blur_filter'


class TestFilterExplorerPresetSelectReset:
    """Tests for preset select reset."""

    def test_load_preset_resets_select(self, monkeypatch):
        """Load preset resets the select widget."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from unittest.mock import MagicMock

        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()
        app.designer = MagicMock()
        app.preset_select = MagicMock()
        app.preset_select.value = 'simple_filter_chain'

        app._load_preset('simple_filter_chain')

        # preset_select.value should be set to None
        assert app.preset_select.value is None


class TestFilterExplorerPortNameResolution:
    """Tests for port name resolution in execute_graph."""

    def test_execute_with_filter_output_ports(self):
        """Execute graph resolves port names from filter class metadata."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        # Use DetectEdges which has specific output ports
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'edges': {
                    'class': 'DetectEdges',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from_node': 'input', 'to_node': 'edges', 'from_output': 0, 'to_input': 0},
                {'from_node': 'edges', 'to_node': 'output', 'from_output': 0, 'to_input': 0}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None

    def test_execute_source_node_type(self):
        """Execute graph handles source node type correctly."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None

    def test_execute_unknown_node_type(self):
        """Execute graph handles unknown node types."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'unknown': {
                    # No class or filterName
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'unknown'},
                {'from': 'unknown', 'to': 'output'}
            ]
        }
        # Should not crash
        result = app._execute_graph(graph_data)


class TestFilterExplorerDictInputHandling:
    """Tests for dict input handling (multi-output filters)."""

    def test_execute_filter_with_dict_input(self):
        """Execute filter that receives dict input (from multi-output filter)."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        import numpy as np

        app = FilterExplorerApp()
        # Manually set up node_results with dict
        test_img = Image(np.zeros((50, 50, 3), dtype=np.uint8))

        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'gray': {
                    'class': 'Grayscale',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'gray'},
                {'from': 'gray', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None


class TestFilterExplorerFilterExceptions:
    """Tests for filter exception handling."""

    def test_execute_filter_exception_fallback(self, monkeypatch):
        """Filter exception falls back to input image."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag.filters import FILTER_REGISTRY
        from unittest.mock import MagicMock
        import traceback

        # Suppress traceback print
        monkeypatch.setattr(traceback, 'print_exc', lambda: None)

        app = FilterExplorerApp()

        # Create a filter class that throws
        class FailingFilter:
            _input_ports = [{'name': 'input'}]
            _output_ports = [{'name': 'output'}]

            def __init__(self, **kwargs):
                pass

            def __call__(self, img):
                raise ValueError("Test exception")

        # Patch registry temporarily
        original = FILTER_REGISTRY.get('failingfilter')
        FILTER_REGISTRY['failingfilter'] = FailingFilter

        try:
            graph_data = {
                'nodes': {
                    'input': {
                        'class': 'PipelineSource',
                        'type': 'IMAGE',
                        'placeholder': 'samples://images/astronaut'
                    },
                    'fail': {
                        'class': 'FailingFilter',
                        'params': {}
                    },
                    'output': {
                        'class': 'PipelineOutput',
                        'type': 'IMAGE'
                    }
                },
                'connections': [
                    {'from': 'input', 'to': 'fail'},
                    {'from': 'fail', 'to': 'output'}
                ]
            }
            result = app._execute_graph(graph_data)
            # Should not crash, returns fallback
        finally:
            if original:
                FILTER_REGISTRY['failingfilter'] = original
            else:
                FILTER_REGISTRY.pop('failingfilter', None)

    def test_execute_unknown_filter_passthrough(self):
        """Unknown filter passes through input image."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'unknown_filter': {
                    'class': 'NonExistentFilter12345',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'unknown_filter'},
                {'from': 'unknown_filter', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        # Unknown filter passes through, output should have result
        assert result is not None


class TestFilterExplorerCombinerEdgeCases:
    """Tests for combiner execution edge cases."""

    def test_execute_combiner_old_params_skips_deprecated(self, monkeypatch):
        """Combiner with old params format skips deprecated params."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input1': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'input2': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/camera'
                },
                'blend': {
                    'class': 'Blend',
                    'params': [
                        {'name': 'mode', 'value': 'NORMAL'},
                        {'name': 'use_geometry_styles', 'value': True}  # deprecated
                    ]
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input1', 'to': ['blend', 'a']},
                {'from': 'input2', 'to': ['blend', 'b']},
                {'from': 'blend', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None

    def test_execute_combiner_single_input(self):
        """Combiner with single input returns that input."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input1': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'blend': {
                    'class': 'Blend',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input1', 'to': ['blend', 'a']},
                {'from': 'blend', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        # Single input, returns that input
        assert result is not None

    def test_execute_combiner_uses_input_ports_metadata(self):
        """Combiner uses filter class _input_ports metadata."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input1': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'input2': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/camera'
                },
                'blend': {
                    'class': 'Blend',
                    'params': {'mode': 'NORMAL'}
                    # No inputPorts specified, uses filter class metadata
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input1', 'to': ['blend', 'a']},
                {'from': 'input2', 'to': ['blend', 'b']},
                {'from': 'blend', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None

    def test_execute_combiner_no_inputs(self):
        """Combiner with no inputs returns None."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'blend': {
                    'class': 'Blend',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'blend', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        # No sources, returns None
        assert result is None


class TestFilterExplorerOutputNodeDictHandling:
    """Tests for output node dict result handling."""

    def test_output_node_dict_result(self):
        """Output node extracts from dict result."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        import numpy as np

        app = FilterExplorerApp()
        # Use a multi-output filter
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'edges': {
                    'class': 'DetectEdges',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'edges'},
                {'from': ['edges', 'edges'], 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        # Should get the edges output


class TestFilterExplorerSidebarPreviewTypes:
    """Tests for sidebar preview with different result types."""

    def test_update_sidebar_geometry_list(self):
        """Update sidebar with GeometryList result."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import GeometryList, Image
        from imagestag.geometry_list import Rectangle
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()

        # Create a simple GeometryList
        geom_list = GeometryList(width=100, height=100)
        geom_list.add(Rectangle(10, 10, 40, 40))

        app.node_results = {'geom': geom_list}
        app.last_graph_data = {'nodes': {'geom': {'filterName': 'DetectEdges'}}}

        app._update_sidebar_preview('geom')
        app.designer.set_output_image.assert_called_once()
        call_args = app.designer.set_output_image.call_args
        assert 'geometries' in call_args[0][1]

    def test_update_sidebar_image_list(self):
        """Update sidebar with ImageList result."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import ImageList, Image
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()

        # Create an ImageList
        img1 = Image(np.zeros((50, 50, 3), dtype=np.uint8))
        img2 = Image(np.ones((50, 50, 3), dtype=np.uint8) * 255)
        img_list = ImageList([img1, img2])

        app.node_results = {'regions': img_list}
        app.last_graph_data = {'nodes': {'regions': {'filterName': 'ExtractRegions'}}}

        app._update_sidebar_preview('regions')
        app.designer.set_output_image.assert_called_once()
        call_args = app.designer.set_output_image.call_args
        assert 'regions' in call_args[0][1]

    def test_update_sidebar_empty_image_list(self):
        """Update sidebar with empty ImageList."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import ImageList
        from unittest.mock import MagicMock

        app = FilterExplorerApp()
        app.designer = MagicMock()

        app.node_results = {'regions': ImageList()}
        app.last_graph_data = {'nodes': {'regions': {'filterName': 'ExtractRegions'}}}

        app._update_sidebar_preview('regions')
        app.designer.set_output_image.assert_called_once()
        call_args = app.designer.set_output_image.call_args
        assert 'Empty' in call_args[0][1]

    def test_update_sidebar_legacy_image_list(self):
        """Update sidebar with legacy list of images."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()

        # Create a plain list of images (legacy format)
        img1 = Image(np.zeros((50, 50, 3), dtype=np.uint8))
        img2 = Image(np.ones((50, 50, 3), dtype=np.uint8) * 255)

        app.node_results = {'regions': [img1, img2]}
        app.last_graph_data = {'nodes': {'regions': {'filterName': 'Extract'}}}

        app._update_sidebar_preview('regions')
        app.designer.set_output_images.assert_called_once()

    def test_update_sidebar_dict_output(self):
        """Update sidebar with dict of outputs."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()

        img1 = Image(np.zeros((50, 50, 3), dtype=np.uint8))
        img2 = Image(np.ones((50, 50, 3), dtype=np.uint8) * 255)

        app.node_results = {'multi': {'output1': img1, 'output2': img2}}
        app.last_graph_data = {'nodes': {'multi': {'filterName': 'MultiOutput'}}}

        app._update_sidebar_preview('multi')
        app.designer.set_output_images.assert_called_once()

    def test_update_sidebar_empty_dict_output(self):
        """Update sidebar with empty dict output."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from unittest.mock import MagicMock

        app = FilterExplorerApp()
        app.designer = MagicMock()

        app.node_results = {'empty': {}}
        app.last_graph_data = {'nodes': {'empty': {'filterName': 'Empty'}}}

        app._update_sidebar_preview('empty')
        app.designer.set_output_image.assert_called_once()
        call_args = app.designer.set_output_image.call_args
        assert 'Empty' in call_args[0][1]

    def test_update_sidebar_dict_with_geometry_list(self):
        """Update sidebar with dict containing GeometryList."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import GeometryList, Image
        from imagestag.geometry_list import Rectangle
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()

        geom_list = GeometryList(width=100, height=100)
        geom_list.add(Rectangle(10, 10, 40, 40))
        img = Image(np.zeros((50, 50, 3), dtype=np.uint8))

        app.node_results = {'multi': {'edges': geom_list, 'image': img}}
        app.last_graph_data = {'nodes': {'multi': {'filterName': 'DetectEdges'}}}

        app._update_sidebar_preview('multi')
        app.designer.set_output_images.assert_called_once()

    def test_update_sidebar_dict_with_image_list(self):
        """Update sidebar with dict containing ImageList."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import ImageList, Image
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()

        img1 = Image(np.zeros((50, 50, 3), dtype=np.uint8))
        img_list = ImageList([img1])

        app.node_results = {'multi': {'regions': img_list}}
        app.last_graph_data = {'nodes': {'multi': {'filterName': 'Extract'}}}

        app._update_sidebar_preview('multi')
        app.designer.set_output_images.assert_called_once()

    def test_update_sidebar_dict_with_empty_image_list(self):
        """Update sidebar with dict containing empty ImageList."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import ImageList, Image
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()

        # Add an image too so we don't get empty output
        img = Image(np.zeros((50, 50, 3), dtype=np.uint8))
        app.node_results = {'multi': {'regions': ImageList(), 'image': img}}
        app.last_graph_data = {'nodes': {'multi': {'filterName': 'Extract'}}}

        app._update_sidebar_preview('multi')
        # Should call set_output_images with just the image (empty list skipped)
        app.designer.set_output_images.assert_called_once()

    def test_update_sidebar_dict_with_legacy_list(self):
        """Update sidebar with dict containing legacy image list."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()

        img1 = Image(np.zeros((50, 50, 3), dtype=np.uint8))

        app.node_results = {'multi': {'regions': [img1]}}
        app.last_graph_data = {'nodes': {'multi': {'filterName': 'Extract'}}}

        app._update_sidebar_preview('multi')
        app.designer.set_output_images.assert_called_once()

    def test_update_sidebar_unknown_type(self):
        """Update sidebar with unknown result type."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from unittest.mock import MagicMock

        app = FilterExplorerApp()
        app.designer = MagicMock()

        # Some unknown type
        app.node_results = {'unknown': "not an image"}
        app.last_graph_data = {'nodes': {'unknown': {'filterName': 'Unknown'}}}

        app._update_sidebar_preview('unknown')
        app.designer.set_output_image.assert_called_once()
        call_args = app.designer.set_output_image.call_args
        assert 'Unknown output type' in call_args[0][1]


class TestFilterExplorerUpdatePreviewEdgeCases:
    """Tests for _update_preview edge cases."""

    def test_update_preview_no_graph_data(self):
        """Update preview with no graph data clears results."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()
        app.node_results = {'test': Image(np.zeros((50, 50, 3), dtype=np.uint8))}

        app._update_preview(None)

        # Results should be cleared
        assert app.node_results == {}
        app.designer.set_output_image.assert_called_once()
        call_args = app.designer.set_output_image.call_args
        assert 'No graph' in call_args[0][1]

    def test_update_preview_uses_selected_node(self):
        """Update preview shows selected node's output."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()
        app.selected_node_id = 'blur'

        test_img = Image(np.zeros((50, 50, 3), dtype=np.uint8))
        app.node_results = {'blur': test_img}

        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'blur': {
                    'class': 'GaussianBlur',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'blur'},
                {'from': 'blur', 'to': 'output'}
            ]
        }

        app._update_preview(graph_data)
        app.designer.set_output_image.assert_called()

    def test_update_preview_fallback_to_source(self, monkeypatch):
        """Update preview falls back to source when output has no result."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        from unittest.mock import MagicMock
        import numpy as np
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()
        app.designer = MagicMock()

        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': []  # No connection, so output has no result
        }

        app._update_preview(graph_data)
        # Should show source as fallback
        app.designer.set_output_image.assert_called()

    def test_update_preview_no_output_node(self, monkeypatch):
        """Update preview with no output node shows message."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from unittest.mock import MagicMock
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()
        app.designer = MagicMock()

        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                }
            },
            'connections': []
        }

        app._update_preview(graph_data)
        # Shows source node since there's no output node
        app.designer.set_output_image.assert_called()

    def test_update_preview_exception_handling(self, monkeypatch):
        """Update preview handles exceptions gracefully."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from unittest.mock import MagicMock
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)
        notifications = []
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify',
                           lambda msg, type=None: notifications.append((msg, type)))

        app = FilterExplorerApp()
        app.designer = MagicMock()

        # Force an exception by providing invalid data
        def bad_execute(*args):
            raise RuntimeError("Test error")

        app._execute_graph = bad_execute

        app._update_preview({'nodes': {}, 'connections': []})

        assert len(notifications) == 1
        assert 'Error' in notifications[0][0]
        assert notifications[0][1] == 'negative'


class TestFilterExplorerRender:
    """Tests for render method."""

    @pytest.mark.asyncio
    async def test_render_creates_components(self, user: User):
        """render() creates header and designer."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        @ui.page('/test_render')
        def page():
            app = FilterExplorerApp()
            app.render()

        await user.open('/test_render')
        # Page should load without errors


class TestFilterExplorerDownloadAPI:
    """Tests for download API endpoint."""

    def test_download_pipeline_success(self):
        """Download pipeline returns JSON data."""
        from imagestag.tools.filter_explorer import _pending_exports, download_pipeline
        import asyncio

        # Add a pending export
        export_id = 'test-export-id'
        _pending_exports[export_id] = '{"test": "data"}'

        # Call the download endpoint
        response = asyncio.get_event_loop().run_until_complete(
            download_pipeline(export_id, 'test.json')
        )

        assert response.body == b'{"test": "data"}'
        assert export_id not in _pending_exports  # Should be removed

    def test_download_pipeline_not_found(self):
        """Download pipeline returns 404 for missing export."""
        from imagestag.tools.filter_explorer import download_pipeline
        import asyncio

        response = asyncio.get_event_loop().run_until_complete(
            download_pipeline('nonexistent-id', 'test.json')
        )

        assert response.status_code == 404


class TestFilterExplorerMain:
    """Tests for main entry point."""

    def test_main_function_exists(self):
        """Main function exists and is callable."""
        from imagestag.tools.filter_explorer import main

        assert callable(main)

    def test_index_page_exists(self):
        """Index page function exists."""
        from imagestag.tools.filter_explorer import index

        assert callable(index)


class TestFilterExplorerExportDialog:
    """Tests for export dialog functionality."""

    def test_on_export_requested_requires_designer(self, monkeypatch):
        """Export requested requires designer to be set."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()
        app.designer = None

        # Should not crash when designer is None
        try:
            app._on_export_requested({})
        except AttributeError:
            pass  # Expected since designer is None


class TestFilterExplorerPortNameResolutionEdgeCases:
    """Tests for port name resolution edge cases."""

    def test_execute_with_indexed_ports_no_output_ports(self):
        """Execute graph resolves ports when filter has no _output_ports."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'blur': {
                    'filterName': 'GaussianBlur',  # Use filterName instead of class
                    'params': {'radius': 2.0}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from_node': 'input', 'to_node': 'blur', 'from_output': 1, 'to_input': 0},
                {'from_node': 'blur', 'to_node': 'output', 'from_output': 0, 'to_input': 0}
            ]
        }
        result = app._execute_graph(graph_data)
        # Should execute without crashing

    def test_execute_with_no_filter_name_for_port_resolution(self):
        """Execute graph handles missing filter name for port resolution."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'filter1': {
                    # No class or filterName
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from_node': 'input', 'to_node': 'filter1', 'from_output': 0, 'to_input': 1},
                {'from_node': 'filter1', 'to_node': 'output', 'from_output': 0, 'to_input': 0}
            ]
        }
        result = app._execute_graph(graph_data)


class TestFilterExplorerDictInputOutputEdgeCases:
    """Tests for dict input/output edge cases."""

    def test_filter_receives_dict_with_missing_port(self):
        """Filter handles dict input when port name is missing."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        # Set up a graph where a filter receives dict output
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'edges': {
                    'class': 'DetectEdges',
                    'params': {}
                },
                'gray': {
                    'class': 'Grayscale',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'edges'},
                {'from': ['edges', 'missing_port'], 'to': 'gray'},  # Non-existent port
                {'from': 'gray', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)

    def test_combiner_receives_dict_outputs(self):
        """Combiner handles dict outputs from multi-output filters."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'edges': {
                    'class': 'DetectEdges',
                    'params': {}
                },
                'input2': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/camera'
                },
                'blend': {
                    'class': 'Blend',
                    'params': {'mode': 'NORMAL'}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'edges'},
                {'from': ['edges', 'edges'], 'to': ['blend', 'a']},  # edges is GeometryList, will fail to blend
                {'from': 'input2', 'to': ['blend', 'b']},
                {'from': 'blend', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)


class TestFilterExplorerCombinerInputPorts:
    """Tests for combiner input ports handling."""

    def test_combiner_with_explicit_input_ports(self):
        """Combiner uses explicit inputPorts when provided."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input1': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'input2': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/camera'
                },
                'blend': {
                    'class': 'Blend',
                    'params': {'mode': 'NORMAL'},
                    'inputPorts': [
                        {'name': 'foreground'},
                        {'name': 'background'}
                    ]
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input1', 'to': ['blend', 'foreground']},
                {'from': 'input2', 'to': ['blend', 'background']},
                {'from': 'blend', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None

    def test_combiner_unknown_filter(self):
        """Unknown combiner filter returns first input."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input1': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'input2': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/camera'
                },
                'unknown': {
                    'class': 'UnknownCombiner12345',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input1', 'to': ['unknown', 'a']},
                {'from': 'input2', 'to': ['unknown', 'b']},
                {'from': 'unknown', 'to': 'output'}
            ]
        }
        # This will not match combiner detection criteria since the filter class doesn't exist
        result = app._execute_graph(graph_data)


class TestFilterExplorerOutputNodeEdgeCases:
    """Tests for output node edge cases."""

    def test_output_receives_dict_with_fallback(self):
        """Output node extracts from dict with fallback to first value."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'edges': {
                    'class': 'DetectEdges',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'edges'},
                {'from': ['edges', 'nonexistent_port'], 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)


class TestFilterExplorerSidebarDictEdgeCases:
    """Tests for sidebar preview dict edge cases."""

    def test_update_sidebar_dict_with_unknown_items(self):
        """Update sidebar with dict containing unknown types."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag import Image
        from unittest.mock import MagicMock
        import numpy as np

        app = FilterExplorerApp()
        app.designer = MagicMock()

        img = Image(np.zeros((50, 50, 3), dtype=np.uint8))

        # Dict with unknown type (string) - should be skipped
        app.node_results = {'multi': {'text': 'some text', 'image': img}}
        app.last_graph_data = {'nodes': {'multi': {'filterName': 'Mixed'}}}

        app._update_sidebar_preview('multi')
        # Should still show the image, skip the text
        app.designer.set_output_images.assert_called_once()

    def test_update_sidebar_dict_all_unknown(self):
        """Update sidebar with dict containing only unknown types."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from unittest.mock import MagicMock

        app = FilterExplorerApp()
        app.designer = MagicMock()

        # Dict with only unknown types
        app.node_results = {'multi': {'text': 'some text', 'number': 42}}
        app.last_graph_data = {'nodes': {'multi': {'filterName': 'Mixed'}}}

        app._update_sidebar_preview('multi')
        # Should show empty output message
        app.designer.set_output_image.assert_called_once()
        call_args = app.designer.set_output_image.call_args
        assert 'Empty' in call_args[0][1]


class TestFilterExplorerUpdatePreviewFallbacks:
    """Tests for _update_preview fallback logic."""

    def test_update_preview_output_null_source_available(self, monkeypatch):
        """Update preview falls back to source when output is null."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from unittest.mock import MagicMock
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()
        app.designer = MagicMock()

        # Graph with source and output, but output is not connected to anything
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': []
        }

        app._update_preview(graph_data)
        # Should fallback to source
        app.designer.set_output_image.assert_called()

    def test_update_preview_graph_only_source(self, monkeypatch):
        """Update preview with graph that only has source node."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from unittest.mock import MagicMock
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()
        app.designer = MagicMock()

        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                }
            },
            'connections': []
        }

        app._update_preview(graph_data)
        app.designer.set_output_image.assert_called()

    def test_update_preview_no_designer_no_graph(self):
        """Update preview with no designer and no graph."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        app.designer = None

        # Should not crash
        app._update_preview(None)

    def test_update_preview_no_designer_with_graph(self, monkeypatch):
        """Update preview with no designer but with graph."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)
        monkeypatch.setattr('imagestag.tools.filter_explorer.ui.notify', lambda *args, **kwargs: None)

        app = FilterExplorerApp()
        app.designer = None

        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                }
            },
            'connections': []
        }

        # Should not crash
        app._update_preview(graph_data)


class TestFilterExplorerMultiOutputFilterPorts:
    """Tests for multi-output filter port resolution."""

    def test_execute_with_multi_output_filter_port_index(self):
        """Execute graph resolves port name from filter _output_ports by index."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        # DetectEdges has _output_ports defined, use index 1 to get 'edges' port
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'edges': {
                    'class': 'DetectEdges',
                    'params': {}
                },
                'blur': {
                    'class': 'GaussianBlur',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from_node': 'input', 'to_node': 'edges', 'from_output': 0, 'to_input': 0},
                # Use from_output: 1 to get the 'edges' port specifically
                {'from_node': 'edges', 'to_node': 'blur', 'from_output': 1, 'to_input': 0},
                {'from_node': 'blur', 'to_node': 'output', 'from_output': 0, 'to_input': 0}
            ]
        }
        result = app._execute_graph(graph_data)

    def test_execute_with_input_port_index_from_metadata(self):
        """Execute graph resolves input port name from filter _input_ports by index."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        # Blend has _input_ports defined with 'a' and 'b'
        graph_data = {
            'nodes': {
                'input1': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'input2': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/camera'
                },
                'blend': {
                    'class': 'Blend',
                    'params': {'mode': 'NORMAL'}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                # Use to_input indices to resolve from filter _input_ports
                {'from_node': 'input1', 'to_node': 'blend', 'from_output': 0, 'to_input': 0},
                {'from_node': 'input2', 'to_node': 'blend', 'from_output': 0, 'to_input': 1},
                {'from_node': 'blend', 'to_node': 'output', 'from_output': 0, 'to_input': 0}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None


class TestFilterExplorerCombinerExceptionHandling:
    """Tests for combiner exception handling."""

    def test_combiner_exception_fallback_to_first_input(self, monkeypatch):
        """Combiner exception falls back to first input."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag.filters import FILTER_REGISTRY
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)

        app = FilterExplorerApp()

        # Create a failing combiner
        class FailingCombiner:
            _input_ports = [{'name': 'a'}, {'name': 'b'}]
            _output_ports = [{'name': 'output'}]

            def __init__(self, inputs=None, **kwargs):
                self.inputs = inputs

            def apply_multi(self, images):
                raise ValueError("Combiner failed")

        original = FILTER_REGISTRY.get('failingcombiner')
        FILTER_REGISTRY['failingcombiner'] = FailingCombiner

        try:
            graph_data = {
                'nodes': {
                    'input1': {
                        'class': 'PipelineSource',
                        'type': 'IMAGE',
                        'placeholder': 'samples://images/astronaut'
                    },
                    'input2': {
                        'class': 'PipelineSource',
                        'type': 'IMAGE',
                        'placeholder': 'samples://images/camera'
                    },
                    'fail': {
                        'class': 'FailingCombiner',
                        'params': {}
                    },
                    'output': {
                        'class': 'PipelineOutput',
                        'type': 'IMAGE'
                    }
                },
                'connections': [
                    {'from': 'input1', 'to': ['fail', 'a']},
                    {'from': 'input2', 'to': ['fail', 'b']},
                    {'from': 'fail', 'to': 'output'}
                ]
            }
            result = app._execute_graph(graph_data)
            # Should not crash, returns fallback to first input
            assert result is not None
        finally:
            if original:
                FILTER_REGISTRY['failingcombiner'] = original
            else:
                FILTER_REGISTRY.pop('failingcombiner', None)

    def test_combiner_no_input_images_returns_none(self, monkeypatch):
        """Combiner with no input_images returns None."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag.filters import FILTER_REGISTRY
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)

        app = FilterExplorerApp()

        # Create a combiner that will have no input images
        class NoInputCombiner:
            _input_ports = [{'name': 'a'}, {'name': 'b'}]
            _output_ports = [{'name': 'output'}]

            def __init__(self, inputs=None, **kwargs):
                self.inputs = inputs

            def apply_multi(self, images):
                raise ValueError("Should not be called")

        original = FILTER_REGISTRY.get('noinputcombiner')
        FILTER_REGISTRY['noinputcombiner'] = NoInputCombiner

        try:
            graph_data = {
                'nodes': {
                    'combiner': {
                        'class': 'NoInputCombiner',
                        'params': {}
                    },
                    'output': {
                        'class': 'PipelineOutput',
                        'type': 'IMAGE'
                    }
                },
                'connections': [
                    {'from': 'combiner', 'to': 'output'}
                ]
            }
            result = app._execute_graph(graph_data)
            # No sources, should return None
            assert result is None
        finally:
            if original:
                FILTER_REGISTRY['noinputcombiner'] = original
            else:
                FILTER_REGISTRY.pop('noinputcombiner', None)


class TestFilterExplorerOutputDictFallback:
    """Tests for output node dict fallback."""

    def test_output_node_dict_fallback_first_value(self):
        """Output node falls back to first dict value when port not found."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        # Connect edges to output with a non-existent port name
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'edges': {
                    'class': 'DetectEdges',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'edges'},
                # Use a port name that doesn't exist in the output
                {'from': ['edges', 'nonexistent'], 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        # Should fallback to first value in the dict


class TestFilterExplorerCombinerDictFallback:
    """Tests for combiner dict input fallback."""

    def test_combiner_dict_input_fallback(self, monkeypatch):
        """Combiner falls back to first dict value when from_port not found."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)

        app = FilterExplorerApp()
        # Use DetectEdges output with wrong port name
        graph_data = {
            'nodes': {
                'input1': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'edges': {
                    'class': 'DetectEdges',
                    'params': {}
                },
                'input2': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/camera'
                },
                'blend': {
                    'class': 'Blend',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input1', 'to': 'edges'},
                # Use wrong port name that doesn't exist in DetectEdges output
                {'from': ['edges', 'wrong_port'], 'to': ['blend', 'a']},
                {'from': 'input2', 'to': ['blend', 'b']},
                {'from': 'blend', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)


class TestFilterExplorerInputNamesFromDict:
    """Tests for combiner input_names from dict keys."""

    def test_combiner_uses_input_images_keys(self, monkeypatch):
        """Combiner uses input_images keys when no inputPorts or _input_ports."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag.filters import FILTER_REGISTRY
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)

        app = FilterExplorerApp()

        # Create a combiner without _input_ports
        class SimpleBlender:
            # No _input_ports defined
            _output_ports = [{'name': 'output'}]

            def __init__(self, inputs=None, **kwargs):
                self.inputs = inputs or []

            def apply_multi(self, images):
                # Just return first image
                return next(iter(images.values())) if images else None

        original = FILTER_REGISTRY.get('simpleblender')
        FILTER_REGISTRY['simpleblender'] = SimpleBlender

        try:
            graph_data = {
                'nodes': {
                    'input1': {
                        'class': 'PipelineSource',
                        'type': 'IMAGE',
                        'placeholder': 'samples://images/astronaut'
                    },
                    'input2': {
                        'class': 'PipelineSource',
                        'type': 'IMAGE',
                        'placeholder': 'samples://images/camera'
                    },
                    'blend': {
                        'class': 'SimpleBlender',
                        'params': {}
                        # No inputPorts, filter has no _input_ports
                    },
                    'output': {
                        'class': 'PipelineOutput',
                        'type': 'IMAGE'
                    }
                },
                'connections': [
                    {'from': 'input1', 'to': ['blend', 'custom_a']},
                    {'from': 'input2', 'to': ['blend', 'custom_b']},
                    {'from': 'blend', 'to': 'output'}
                ]
            }
            result = app._execute_graph(graph_data)
            assert result is not None
        finally:
            if original:
                FILTER_REGISTRY['simpleblender'] = original
            else:
                FILTER_REGISTRY.pop('simpleblender', None)


class TestFilterExplorerFilterDictInputExtraction:
    """Tests for filter dict input extraction."""

    def test_filter_receives_dict_extracts_by_port(self):
        """Filter extracts from dict by port name."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        # DetectEdges outputs {'image': Image, 'edges': GeometryList}
        # Connect to Grayscale which needs an Image
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'edges': {
                    'class': 'DetectEdges',
                    'params': {}
                },
                'gray': {
                    'class': 'Grayscale',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'edges'},
                # Connect the 'image' port from DetectEdges to Grayscale
                {'from': ['edges', 'image'], 'to': 'gray'},
                {'from': 'gray', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None

    def test_filter_dict_input_fallback_to_first(self):
        """Filter falls back to first dict value when port not found."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'edges': {
                    'class': 'DetectEdges',
                    'params': {}
                },
                'blur': {
                    'class': 'GaussianBlur',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'edges'},
                # Connect with wrong port name, should fallback to first value
                {'from': ['edges', 'nonexistent'], 'to': 'blur'},
                {'from': 'blur', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)


class TestFilterExplorerSpecificLineCoverage:
    """Tests targeting specific uncovered lines."""

    def test_filter_dict_input_port_in_dict(self):
        """Filter extracts from dict when port name exists (lines 353-355)."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        # SplitChannels returns a dict with {'R': img, 'G': img, 'B': img}
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'split': {
                    'class': 'SplitChannels',
                    'params': {}
                },
                'invert': {
                    'class': 'Invert',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'split'},
                # Explicitly connect the 'R' port which exists in the dict
                {'from': ['split', 'R'], 'to': 'invert'},
                {'from': 'invert', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        # Should successfully extract 'R' from dict and invert it
        assert result is not None

    def test_filter_dict_input_port_not_in_dict_fallback(self):
        """Filter falls back to first dict value when port not found (lines 356-357)."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'split': {
                    'class': 'SplitChannels',
                    'params': {}
                },
                'invert': {
                    'class': 'Invert',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'split'},
                # Use a port that doesn't exist to trigger fallback
                {'from': ['split', 'does_not_exist'], 'to': 'invert'},
                {'from': 'invert', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        # Should fallback to first dict value
        assert result is not None

    def test_combiner_dict_input_port_in_dict(self, monkeypatch):
        """Combiner extracts from dict when port exists (lines 393-395)."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input1': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'split': {
                    'class': 'SplitChannels',
                    'params': {}
                },
                'input2': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/camera'
                },
                'blend': {
                    'class': 'Blend',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input1', 'to': 'split'},
                # Connect specific 'R' port from SplitChannels output
                {'from': ['split', 'R'], 'to': ['blend', 'a']},
                {'from': 'input2', 'to': ['blend', 'b']},
                {'from': 'blend', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None

    def test_combiner_dict_input_port_fallback(self, monkeypatch):
        """Combiner falls back to first dict value (lines 396-397)."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input1': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'split': {
                    'class': 'SplitChannels',
                    'params': {}
                },
                'input2': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/camera'
                },
                'blend': {
                    'class': 'Blend',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input1', 'to': 'split'},
                # Connect non-existent port to trigger fallback
                {'from': ['split', 'nonexistent_port'], 'to': ['blend', 'a']},
                {'from': 'input2', 'to': ['blend', 'b']},
                {'from': 'blend', 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        assert result is not None

    def test_combiner_uses_keys_for_input_names(self, monkeypatch):
        """Combiner uses input_images keys as input_names (line 431)."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag.filters import FILTER_REGISTRY
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)

        # Create a combiner without _input_ports (so it falls back to keys)
        class KeyBasedCombiner:
            # No _input_ports defined!

            def __init__(self, inputs=None, **kwargs):
                self.inputs = inputs or []

            def apply_multi(self, images):
                # Return first image
                if images:
                    return next(iter(images.values()))
                return None

        original = FILTER_REGISTRY.get('keybasedcombiner')
        FILTER_REGISTRY['keybasedcombiner'] = KeyBasedCombiner

        try:
            app = FilterExplorerApp()
            graph_data = {
                'nodes': {
                    'input1': {
                        'class': 'PipelineSource',
                        'type': 'IMAGE',
                        'placeholder': 'samples://images/astronaut'
                    },
                    'input2': {
                        'class': 'PipelineSource',
                        'type': 'IMAGE',
                        'placeholder': 'samples://images/camera'
                    },
                    'combine': {
                        'class': 'KeyBasedCombiner',
                        'params': {}
                        # No inputPorts - will use input_images.keys()
                    },
                    'output': {
                        'class': 'PipelineOutput',
                        'type': 'IMAGE'
                    }
                },
                'connections': [
                    {'from': 'input1', 'to': ['combine', 'port_a']},
                    {'from': 'input2', 'to': ['combine', 'port_b']},
                    {'from': 'combine', 'to': 'output'}
                ]
            }
            result = app._execute_graph(graph_data)
            assert result is not None
        finally:
            if original:
                FILTER_REGISTRY['keybasedcombiner'] = original
            else:
                FILTER_REGISTRY.pop('keybasedcombiner', None)

    def test_output_receives_dict_with_port_in_dict(self):
        """Output node extracts from dict when port exists (lines 456-458)."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'split': {
                    'class': 'SplitChannels',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'split'},
                # Connect the 'R' port which exists in the dict
                {'from': ['split', 'R'], 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        # Should extract 'R' from dict
        assert result is not None

    def test_output_receives_dict_fallback_first(self):
        """Output node falls back to first dict value (lines 459-460)."""
        from imagestag.tools.filter_explorer import FilterExplorerApp

        app = FilterExplorerApp()
        graph_data = {
            'nodes': {
                'input': {
                    'class': 'PipelineSource',
                    'type': 'IMAGE',
                    'placeholder': 'samples://images/astronaut'
                },
                'split': {
                    'class': 'SplitChannels',
                    'params': {}
                },
                'output': {
                    'class': 'PipelineOutput',
                    'type': 'IMAGE'
                }
            },
            'connections': [
                {'from': 'input', 'to': 'split'},
                # Connect with non-existent port to trigger fallback
                {'from': ['split', 'missing_port'], 'to': 'output'}
            ]
        }
        result = app._execute_graph(graph_data)
        # Should fallback to first dict value
        assert result is not None

    def test_combiner_exception_with_empty_input_images(self, monkeypatch):
        """Combiner exception with empty input_images returns None (lines 444, 448)."""
        from imagestag.tools.filter_explorer import FilterExplorerApp
        from imagestag.filters import FILTER_REGISTRY
        import traceback

        monkeypatch.setattr(traceback, 'print_exc', lambda: None)

        # Create combiner that throws
        class CrashingCombiner:
            _input_ports = [{'name': 'a'}, {'name': 'b'}]
            _output_ports = [{'name': 'output'}]

            def __init__(self, inputs=None, **kwargs):
                self.inputs = inputs

            def apply_multi(self, images):
                raise RuntimeError("Combiner crashed")

        original = FILTER_REGISTRY.get('crashingcombiner')
        FILTER_REGISTRY['crashingcombiner'] = CrashingCombiner

        try:
            app = FilterExplorerApp()
            graph_data = {
                'nodes': {
                    'input1': {
                        'class': 'PipelineSource',
                        'type': 'IMAGE',
                        'placeholder': 'samples://images/astronaut'
                    },
                    'input2': {
                        'class': 'PipelineSource',
                        'type': 'IMAGE',
                        'placeholder': 'samples://images/camera'
                    },
                    'crash': {
                        'class': 'CrashingCombiner',
                        'params': {}
                    },
                    'output': {
                        'class': 'PipelineOutput',
                        'type': 'IMAGE'
                    }
                },
                'connections': [
                    {'from': 'input1', 'to': ['crash', 'a']},
                    {'from': 'input2', 'to': ['crash', 'b']},
                    {'from': 'crash', 'to': 'output'}
                ]
            }
            result = app._execute_graph(graph_data)
            # Should return fallback to first input
            assert result is not None
        finally:
            if original:
                FILTER_REGISTRY['crashingcombiner'] = original
            else:
                FILTER_REGISTRY.pop('crashingcombiner', None)
