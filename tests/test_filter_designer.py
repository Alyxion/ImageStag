"""Tests for FilterDesigner component and utilities."""

import pytest
from nicegui import ui
from nicegui.testing import User


# =============================================================================
# Utility Function Tests (no UI required)
# =============================================================================

class TestGetFilterList:
    """Tests for get_filter_list utility."""

    def test_returns_list(self):
        from imagestag.components.filter_designer import get_filter_list

        filters = get_filter_list()
        assert isinstance(filters, list)
        assert len(filters) > 0

    def test_filter_has_required_fields(self):
        from imagestag.components.filter_designer import get_filter_list

        filters = get_filter_list()
        for f in filters[:5]:  # Check first 5
            assert 'name' in f
            assert 'description' in f
            assert 'params' in f
            assert 'inputs' in f
            assert 'outputs' in f

    def test_skips_multi_input_filters(self):
        from imagestag.components.filter_designer import get_filter_list

        filters = get_filter_list()
        names = [f['name'] for f in filters]
        assert 'Composite' not in names
        assert 'MaskApply' not in names
        assert 'MergeChannels' not in names

    def test_params_have_types(self):
        from imagestag.components.filter_designer import get_filter_list

        filters = get_filter_list()
        # Find a filter with params
        for f in filters:
            if f['params']:
                param = f['params'][0]
                assert 'name' in param
                assert 'type' in param
                assert 'default' in param
                break

    def test_enum_params_have_options(self):
        from imagestag.components.filter_designer import get_filter_list

        filters = get_filter_list()
        # Find Blend filter which has mode enum
        blend = next((f for f in filters if f['name'] == 'Blend'), None)
        if blend:
            mode_param = next((p for p in blend['params'] if p['name'] == 'mode'), None)
            if mode_param:
                assert mode_param['type'] == 'select'
                assert 'options' in mode_param
                assert len(mode_param['options']) > 0


class TestGetCategoryList:
    """Tests for get_category_list utility."""

    def test_returns_list(self):
        from imagestag.components.filter_designer import get_category_list

        categories = get_category_list()
        assert isinstance(categories, list)
        assert len(categories) > 0

    def test_category_has_name_and_filters(self):
        from imagestag.components.filter_designer import get_category_list

        categories = get_category_list()
        for cat in categories:
            assert 'name' in cat
            assert 'filters' in cat
            assert isinstance(cat['filters'], list)

    def test_filters_have_name_and_description(self):
        from imagestag.components.filter_designer import get_category_list

        categories = get_category_list()
        for cat in categories:
            for f in cat['filters']:
                assert 'name' in f
                assert 'description' in f


class TestToSnakeCase:
    """Tests for _to_snake_case utility."""

    def test_camel_to_snake(self):
        from imagestag.components.filter_designer import _to_snake_case

        assert _to_snake_case('GaussianBlur') == 'gaussian_blur'
        assert _to_snake_case('SplitChannels') == 'split_channels'

    def test_simple_name(self):
        from imagestag.components.filter_designer import _to_snake_case

        assert _to_snake_case('Blur') == 'blur'
        assert _to_snake_case('Gray') == 'gray'

    def test_uppercase_abbreviation(self):
        from imagestag.components.filter_designer import _to_snake_case

        # All caps stay lowercase (no underscores between each letter)
        assert _to_snake_case('CLAHE') == 'clahe'


class TestGetParamRange:
    """Tests for _get_param_range utility."""

    def test_factor_range(self):
        from imagestag.components.filter_designer import _get_param_range

        min_val, max_val, step = _get_param_range('factor', 1.0, 'float')
        assert min_val == 0.0
        assert max_val == 3.0
        assert step == 0.1

    def test_radius_range(self):
        from imagestag.components.filter_designer import _get_param_range

        min_val, max_val, step = _get_param_range('radius', 2.0, 'float')
        assert min_val == 0.0
        assert max_val == 20.0
        assert step == 0.5

    def test_threshold_range(self):
        from imagestag.components.filter_designer import _get_param_range

        min_val, max_val, step = _get_param_range('threshold', 128, 'int')
        assert min_val == 0
        assert max_val == 255
        assert step == 1

    def test_angle_range(self):
        from imagestag.components.filter_designer import _get_param_range

        min_val, max_val, step = _get_param_range('angle', 45.0, 'float')
        assert min_val == -180.0
        assert max_val == 180.0
        assert step == 5.0

    def test_bool_type_range(self):
        from imagestag.components.filter_designer import _get_param_range

        min_val, max_val, step = _get_param_range('enabled', True, 'bool')
        assert (min_val, max_val, step) == (0, 1, 1)

    def test_string_type_range(self):
        from imagestag.components.filter_designer import _get_param_range

        min_val, max_val, step = _get_param_range('mode', 'auto', 'str')
        assert (min_val, max_val, step) == (0, 1, 1)

    def test_generic_int_range(self):
        from imagestag.components.filter_designer import _get_param_range

        min_val, max_val, step = _get_param_range('count', 10, 'int')
        assert min_val == 0
        assert max_val >= 30  # 3x default
        assert step == 1

    def test_generic_float_range(self):
        from imagestag.components.filter_designer import _get_param_range

        min_val, max_val, step = _get_param_range('amount', 2.0, 'float')
        assert min_val == 0.0
        assert max_val >= 6.0  # 3x default
        assert step == 0.1


# =============================================================================
# FilterDesigner Component Tests (UI tests)
# =============================================================================

class TestFilterDesignerComponent:
    """Tests for FilterDesigner NiceGUI component."""

    @pytest.mark.asyncio
    async def test_component_initializes(self, user: User):
        """FilterDesigner can be created and mounted."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_designer_init')
        def page():
            FilterDesigner()

        await user.open('/test_designer_init')

    @pytest.mark.asyncio
    async def test_component_with_callbacks(self, user: User):
        """FilterDesigner accepts callbacks."""
        from imagestag.components import FilterDesigner

        graph_changes = []

        def on_graph_change(data):
            graph_changes.append(data)

        @ui.page('/test_designer_callbacks')
        def page():
            FilterDesigner(on_graph_change=on_graph_change)

        await user.open('/test_designer_callbacks')

    @pytest.mark.asyncio
    async def test_component_with_custom_filters(self, user: User):
        """FilterDesigner can use custom filter list."""
        from imagestag.components import FilterDesigner

        custom_filters = [
            {
                'name': 'CustomFilter',
                'description': 'A custom filter',
                'params': [{'name': 'value', 'type': 'float', 'default': 1.0, 'min': 0, 'max': 10, 'step': 0.1}],
                'inputs': [{'name': 'input'}],
                'outputs': [{'name': 'output'}],
            }
        ]
        custom_categories = [
            {'name': 'Custom', 'filters': [{'name': 'CustomFilter', 'description': 'A custom filter'}]}
        ]

        @ui.page('/test_designer_custom')
        def page():
            FilterDesigner(filters=custom_filters, categories=custom_categories)

        await user.open('/test_designer_custom')

    @pytest.mark.asyncio
    async def test_component_name_generation(self, user: User):
        """FilterDesigner generates unique names."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_designer_names')
        def page():
            designer = FilterDesigner()
            name1 = designer._generate_name('source')
            name2 = designer._generate_name('source')
            assert name1 == 'input'
            assert name2 == 'input_2'

            name3 = designer._generate_name('filter', 'GaussianBlur')
            name4 = designer._generate_name('filter', 'GaussianBlur')
            assert name3 == 'gaussian_blur'
            assert name4 == 'gaussian_blur_2'

        await user.open('/test_designer_names')

    @pytest.mark.asyncio
    async def test_component_graph_state(self, user: User):
        """FilterDesigner maintains graph state."""
        from imagestag.components import FilterDesigner
        from imagestag.filters.graph import FilterGraph

        @ui.page('/test_designer_graph')
        def page():
            designer = FilterDesigner()
            assert isinstance(designer.graph, FilterGraph)

        await user.open('/test_designer_graph')

    @pytest.mark.asyncio
    async def test_component_source_images(self, user: User):
        """FilterDesigner accepts source images list."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_designer_sources')
        def page():
            FilterDesigner(
                source_images=['astronaut', 'camera', 'coins'],
                default_source_image='camera'
            )

        await user.open('/test_designer_sources')

    @pytest.mark.asyncio
    async def test_component_show_nodes_options(self, user: User):
        """FilterDesigner respects show_source_node and show_output_node."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_designer_nodes')
        def page():
            FilterDesigner(
                show_source_node=False,
                show_output_node=False
            )

        await user.open('/test_designer_nodes')


class TestFilterDesignerEventHandlers:
    """Tests for FilterDesigner event handlers."""

    @pytest.mark.asyncio
    async def test_handle_node_added_source(self, user: User):
        """Handle adding a source node."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_node_added_source')
        def page():
            changes = []
            designer = FilterDesigner(on_graph_change=lambda d: changes.append(d))

            # Simulate node added event
            class MockEvent:
                args = {'id': '1', 'type': 'source', 'x': 100, 'y': 50, 'sourceImage': 'astronaut'}

            designer._handle_node_added(MockEvent())
            assert 'input' in designer.graph.nodes
            assert len(changes) == 1

        await user.open('/test_node_added_source')

    @pytest.mark.asyncio
    async def test_handle_node_added_filter(self, user: User):
        """Handle adding a filter node."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_node_added_filter')
        def page():
            designer = FilterDesigner()

            class MockEvent:
                args = {'id': '2', 'type': 'filter', 'filterName': 'GaussianBlur', 'x': 200, 'y': 50}

            designer._handle_node_added(MockEvent())
            assert 'gaussian_blur' in designer.graph.nodes
            assert designer.graph.nodes['gaussian_blur'].filter is not None

        await user.open('/test_node_added_filter')

    @pytest.mark.asyncio
    async def test_handle_node_added_output(self, user: User):
        """Handle adding an output node."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_node_added_output')
        def page():
            designer = FilterDesigner()

            class MockEvent:
                args = {'id': '3', 'type': 'output', 'x': 300, 'y': 50}

            designer._handle_node_added(MockEvent())
            assert 'output' in designer.graph.nodes
            assert designer.graph.nodes['output'].is_output

        await user.open('/test_node_added_output')

    @pytest.mark.asyncio
    async def test_handle_node_removed(self, user: User):
        """Handle removing a node."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_node_removed')
        def page():
            changes = []
            designer = FilterDesigner(on_graph_change=lambda d: changes.append(d))

            # Add a node first
            class AddEvent:
                args = {'id': '1', 'type': 'filter', 'filterName': 'Blur', 'x': 100, 'y': 50}

            designer._handle_node_added(AddEvent())
            assert 'blur' in designer.graph.nodes

            # Remove it
            class RemoveEvent:
                args = {'id': '1'}

            designer._handle_node_removed(RemoveEvent())
            assert 'blur' not in designer.graph.nodes

        await user.open('/test_node_removed')

    @pytest.mark.asyncio
    async def test_handle_connection_added(self, user: User):
        """Handle adding a connection."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_connection_added')
        def page():
            changes = []
            designer = FilterDesigner(on_graph_change=lambda d: changes.append(d))

            # Add two nodes
            class Node1:
                args = {'id': '1', 'type': 'source', 'x': 0, 'y': 0}

            class Node2:
                args = {'id': '2', 'type': 'filter', 'filterName': 'Blur', 'x': 100, 'y': 0}

            designer._handle_node_added(Node1())
            designer._handle_node_added(Node2())

            # Add connection
            class ConnEvent:
                args = {'fromNode': '1', 'toNode': '2', 'fromOutput': 0, 'toInput': 0}

            designer._handle_connection_added(ConnEvent())
            assert len(designer.graph.connections) == 1

        await user.open('/test_connection_added')

    @pytest.mark.asyncio
    async def test_handle_connection_removed(self, user: User):
        """Handle removing a connection."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_connection_removed')
        def page():
            designer = FilterDesigner()

            # Add nodes and connection
            class Node1:
                args = {'id': '1', 'type': 'source', 'x': 0, 'y': 0}

            class Node2:
                args = {'id': '2', 'type': 'filter', 'filterName': 'Blur', 'x': 100, 'y': 0}

            class ConnEvent:
                args = {'fromNode': '1', 'toNode': '2', 'fromOutput': 0, 'toInput': 0}

            designer._handle_node_added(Node1())
            designer._handle_node_added(Node2())
            designer._handle_connection_added(ConnEvent())
            assert len(designer.graph.connections) == 1

            # Remove connection
            designer._handle_connection_removed(ConnEvent())
            assert len(designer.graph.connections) == 0

        await user.open('/test_connection_removed')

    @pytest.mark.asyncio
    async def test_handle_param_changed(self, user: User):
        """Handle parameter change."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_param_changed')
        def page():
            changes = []
            designer = FilterDesigner(on_graph_change=lambda d: changes.append(d))

            # Add a filter node
            class NodeEvent:
                args = {'id': '1', 'type': 'filter', 'filterName': 'GaussianBlur', 'x': 0, 'y': 0}

            designer._handle_node_added(NodeEvent())

            # Change parameter
            class ParamEvent:
                args = {'nodeId': '1', 'param': 'radius', 'value': 5.0}

            designer._handle_param_changed(ParamEvent())
            assert designer.graph.nodes['gaussian_blur'].filter.radius == 5.0

        await user.open('/test_param_changed')

    @pytest.mark.asyncio
    async def test_handle_layout_changed(self, user: User):
        """Handle layout change."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_layout_changed')
        def page():
            designer = FilterDesigner()

            # Add a node
            class NodeEvent:
                args = {'id': '1', 'type': 'filter', 'filterName': 'Blur', 'x': 0, 'y': 0}

            designer._handle_node_added(NodeEvent())

            # Change layout
            class LayoutEvent:
                args = {'nodeId': '1', 'x': 200, 'y': 150}

            designer._handle_layout_changed(LayoutEvent())
            assert designer.graph.nodes['blur'].editor == {'x': 200, 'y': 150}

        await user.open('/test_layout_changed')

    @pytest.mark.asyncio
    async def test_handle_execute(self, user: User):
        """Handle execute event."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_execute')
        def page():
            executed = []
            designer = FilterDesigner(on_execute=lambda d: executed.append(d))

            class ExecEvent:
                args = {}

            designer._handle_execute(ExecEvent())
            assert len(executed) == 1

        await user.open('/test_execute')

    @pytest.mark.asyncio
    async def test_handle_execute_fallback(self, user: User):
        """Handle execute falls back to on_graph_change."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_execute_fallback')
        def page():
            changes = []
            designer = FilterDesigner(on_graph_change=lambda d: changes.append(d))

            class ExecEvent:
                args = {}

            designer._handle_execute(ExecEvent())
            assert len(changes) == 1

        await user.open('/test_execute_fallback')

    @pytest.mark.asyncio
    async def test_handle_node_selected(self, user: User):
        """Handle node selection."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_node_selected')
        def page():
            selected = []
            designer = FilterDesigner(on_node_selected=lambda d: selected.append(d))

            class SelectEvent:
                args = {'id': '1', 'type': 'filter'}

            designer._handle_node_selected(SelectEvent())
            assert len(selected) == 1
            assert selected[0]['id'] == '1'

        await user.open('/test_node_selected')

    @pytest.mark.asyncio
    async def test_handle_callbacks(self, user: User):
        """Handle various callback events."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_callbacks')
        def page():
            uploads = []
            notifies = []
            exports = []
            imports = []

            designer = FilterDesigner(
                on_notify=lambda d: notifies.append(d),
                on_export_requested=lambda d: exports.append(d),
                on_import_completed=lambda d: imports.append(d),
            )
            designer.set_upload_handler(lambda d: uploads.append(d))

            class UploadEvent:
                args = {'nodeId': '1', 'fileName': 'test.png', 'data': 'base64data'}

            class NotifyEvent:
                args = {'message': 'Test notification'}

            class ExportEvent:
                args = {'format': 'json'}

            class ImportEvent:
                args = {'success': True}

            designer._handle_image_upload(UploadEvent())
            designer._handle_notify(NotifyEvent())
            designer._handle_export_requested(ExportEvent())
            designer._handle_import_completed(ImportEvent())

            assert len(uploads) == 1
            assert len(notifies) == 1
            assert len(exports) == 1
            assert len(imports) == 1

        await user.open('/test_callbacks')

    @pytest.mark.asyncio
    async def test_handle_preset_loaded(self, user: User):
        """Handle preset loaded event."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_preset_loaded')
        def page():
            changes = []
            designer = FilterDesigner(on_graph_change=lambda d: changes.append(d))

            class PresetEvent:
                args = {'idToName': {'input': '1', 'blur': '2', 'output': '3'}}

            designer._handle_preset_loaded(PresetEvent())
            assert designer._id_to_name == {'1': 'input', '2': 'blur', '3': 'output'}

        await user.open('/test_preset_loaded')


class TestFilterDesignerMethods:
    """Tests for FilterDesigner methods."""

    @pytest.mark.asyncio
    async def test_get_graph_data(self, user: User):
        """get_graph_data returns current graph state."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_get_graph_data')
        def page():
            designer = FilterDesigner()
            data = designer.get_graph_data()
            assert isinstance(data, dict)
            # Graph can have 'nodes' or 'branches' depending on format
            assert 'nodes' in data or 'branches' in data

        await user.open('/test_get_graph_data')

    @pytest.mark.asyncio
    async def test_clear_graph(self, user: User):
        """clear_graph resets the graph."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_clear_graph')
        def page():
            designer = FilterDesigner()

            # Add a node
            class NodeEvent:
                args = {'id': '1', 'type': 'filter', 'filterName': 'Blur', 'x': 0, 'y': 0}

            designer._handle_node_added(NodeEvent())
            assert len(designer.graph.nodes) > 0

            # Clear
            designer.clear_graph()
            assert len(designer.graph.nodes) == 0
            assert len(designer._id_to_name) == 0
            assert len(designer._name_counter) == 0

        await user.open('/test_clear_graph')

    @pytest.mark.asyncio
    async def test_load_graph(self, user: User):
        """load_graph loads a FilterGraph."""
        from imagestag.components import FilterDesigner
        from imagestag.filters.graph import FilterGraph, GraphNode
        from imagestag.filters.source import PipelineSource

        @ui.page('/test_load_graph')
        def page():
            designer = FilterDesigner()

            # Create a graph
            graph = FilterGraph()
            graph.add_node('input', GraphNode(name='input', source=PipelineSource.image()), x=0, y=0)

            designer.load_graph(graph)
            assert 'input' in designer.graph.nodes

        await user.open('/test_load_graph')

    @pytest.mark.asyncio
    async def test_load_graph_invalid_type(self, user: User):
        """load_graph raises TypeError for invalid input."""
        from imagestag.components import FilterDesigner

        @ui.page('/test_load_graph_invalid')
        def page():
            designer = FilterDesigner()

            try:
                designer.load_graph("not a graph")
                assert False, "Should have raised TypeError"
            except TypeError as e:
                assert "Expected FilterGraph" in str(e)

        await user.open('/test_load_graph_invalid')


class TestBuildPipeline:
    """Tests for FilterDesigner.build_pipeline static method."""

    def test_build_pipeline_empty(self):
        """build_pipeline returns None for empty graph."""
        from imagestag.components.filter_designer import FilterDesigner

        result = FilterDesigner.build_pipeline({'nodes': {}})
        assert result is None

    def test_build_linear_pipeline(self):
        """build_pipeline creates linear pipeline."""
        from imagestag.components.filter_designer import FilterDesigner
        from imagestag.filters.pipeline import FilterPipeline

        graph_data = {
            'nodes': {
                'source': {'type': 'source'},
                'blur': {'type': 'filter', 'filterName': 'GaussianBlur', 'params': [{'name': 'radius', 'value': 2.0}]},
                'output': {'type': 'output'},
            },
            'connections': [
                {'from_node': 'source', 'to_node': 'blur'},
                {'from_node': 'blur', 'to_node': 'output'},
            ],
        }

        result = FilterDesigner.build_pipeline(graph_data)
        assert isinstance(result, FilterPipeline)
        assert len(result.filters) == 1

    def test_build_branching_pipeline(self):
        """build_pipeline creates FilterGraph for branching."""
        from imagestag.components.filter_designer import FilterDesigner
        from imagestag.filters.graph import FilterGraph

        graph_data = {
            'nodes': {
                'source': {'type': 'source'},
                'blur': {'type': 'filter', 'filterName': 'GaussianBlur', 'params': []},
                'gray': {'type': 'filter', 'filterName': 'Grayscale', 'params': []},
                'blend': {'type': 'combiner', 'params': [{'name': 'mode', 'value': 'NORMAL'}]},
            },
            'connections': [
                {'from_node': 'source', 'to_node': 'blur'},
                {'from_node': 'source', 'to_node': 'gray'},
                {'from_node': 'blur', 'to_node': 'blend'},
                {'from_node': 'gray', 'to_node': 'blend'},
            ],
        }

        result = FilterDesigner.build_pipeline(graph_data)
        assert isinstance(result, FilterGraph)

    def test_build_pipeline_no_source(self):
        """build_pipeline handles missing source."""
        from imagestag.components.filter_designer import FilterDesigner

        graph_data = {
            'nodes': {
                'blur': {'type': 'filter', 'filterName': 'GaussianBlur', 'params': []},
                'output': {'type': 'output'},
            },
            'connections': [
                {'from_node': 'blur', 'to_node': 'output'},
            ],
        }

        result = FilterDesigner.build_pipeline(graph_data)
        # Should still work, starting from first filter
        assert result is not None
