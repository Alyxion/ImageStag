"""FilterDesigner - Reusable node-based filter pipeline editor.

A visual graph editor for building ImageStag filter pipelines using Drawflow.
Implemented as a proper NiceGUI custom component with bundled JavaScript.

Usage:
    from imagestag.components import FilterDesigner

    def on_graph_change(data):
        # data contains nodes and connections
        pipeline = build_pipeline_from_graph(data)
        result = pipeline.apply(source_image)
        designer.set_output_image(result_base64, "512x512 | RGB")

    designer = FilterDesigner(
        filters=filter_list,
        categories=category_list,
        on_graph_change=on_graph_change,
    )
"""

from __future__ import annotations

from dataclasses import fields, MISSING
from pathlib import Path
from typing import Callable

from nicegui.element import Element
from nicegui.events import GenericEventArguments, handle_event

from imagestag.filters import (
    Filter,
    FilterPipeline,
    FilterGraph,
    FilterContext,
    FILTER_REGISTRY,
    PipelineSource,
)
from imagestag.filters.graph import Blend, BlendMode, GraphNode, GraphConnection
from imagestag.filters.demo_metadata import (
    CATEGORIES,
    get_filter_metadata,
    get_filters_by_category,
)


def get_filter_list() -> list[dict]:
    """Get list of all filters with their metadata and parameters."""
    from enum import Enum
    import typing

    # Skip multi-input filters that need special handling
    SKIP_FILTERS = {'Composite', 'MaskApply', 'MergeChannels'}

    filters = []
    for name in FILTER_REGISTRY.keys():
        # Skip multi-input combiners
        if name in SKIP_FILTERS:
            continue

        meta = get_filter_metadata(name)
        filter_cls = FILTER_REGISTRY.get(name)

        # Extract parameters from dataclass fields
        params = []
        if filter_cls:
            for fld in fields(filter_cls):
                if fld.name.startswith('_'):
                    continue

                # Skip 'inputs' field - it's for multi-input configuration, not UI
                # Skip 'use_geometry_styles' - always use custom colors from UI
                if fld.name in ('inputs', 'use_geometry_styles'):
                    continue

                # Get the actual type, handling Optional and other typing constructs
                field_type = fld.type

                # Resolve string annotations to actual types
                if isinstance(field_type, str):
                    # Try to resolve from filter class module
                    import sys
                    filter_module = sys.modules.get(filter_cls.__module__)
                    if filter_module:
                        field_type = getattr(filter_module, field_type, field_type)

                origin = typing.get_origin(field_type)
                if origin is typing.Union:
                    # Handle Optional[X] = Union[X, None]
                    args = typing.get_args(field_type)
                    field_type = args[0] if args else field_type

                # Check if it's an Enum type
                is_enum = False
                enum_options = []
                try:
                    if isinstance(field_type, type) and issubclass(field_type, Enum):
                        is_enum = True
                        enum_options = [e.name for e in field_type]
                except TypeError:
                    pass

                type_str = str(fld.type).lower()
                param_type = 'float'
                default_val = None

                # Check if metadata specifies a type for this param
                param_meta = meta.get('params', {}).get(fld.name, {})
                meta_type = param_meta.get('type')

                if meta_type == 'color':
                    param_type = 'color'
                elif meta_type == 'select':
                    param_type = 'select'
                elif is_enum:
                    param_type = 'select'
                    # Get default value name
                    if fld.default is not MISSING:
                        default_val = fld.default.name if isinstance(fld.default, Enum) else str(fld.default)
                    else:
                        default_val = enum_options[0] if enum_options else ''
                elif 'int' in type_str:
                    param_type = 'int'
                elif 'bool' in type_str:
                    param_type = 'bool'
                elif 'str' in type_str:
                    # Check if param name suggests color
                    name_lower = fld.name.lower()
                    if 'color' in name_lower and fld.default and isinstance(fld.default, str) and fld.default.startswith('#'):
                        param_type = 'color'
                    else:
                        param_type = 'str'
                elif 'list' in type_str or 'dict' in type_str:
                    # Skip complex types
                    continue

                # Handle MISSING default values for non-enum types
                if default_val is None:
                    if fld.default is MISSING:
                        if param_type == 'float':
                            default_val = 1.0
                        elif param_type == 'int':
                            default_val = 0
                        elif param_type == 'bool':
                            default_val = False
                        else:
                            default_val = ''
                    else:
                        default_val = fld.default

                # Infer ranges from param names
                min_val, max_val, step = _get_param_range(fld.name, default_val, param_type)

                param_def = {
                    'name': fld.name,
                    'type': param_type,
                    'default': default_val,
                    'min': min_val,
                    'max': max_val,
                    'step': step,
                }
                # Add options from enum or metadata
                if is_enum:
                    param_def['options'] = enum_options
                elif meta_type == 'select' and 'options' in param_meta:
                    param_def['options'] = param_meta['options']

                params.append(param_def)

        # Get port specifications
        inputs = filter_cls.get_input_ports() if filter_cls else [{'name': 'input'}]
        outputs = filter_cls.get_output_ports() if filter_cls else [{'name': 'output'}]

        filters.append({
            'name': name,
            'description': meta.get('description', ''),
            'params': params,
            'inputs': inputs,
            'outputs': outputs,
        })

    return filters


def get_category_list() -> list[dict]:
    """Get list of categories with their filters."""
    # Skip multi-input filters that need special handling
    SKIP_FILTERS = {'Composite', 'MaskApply', 'MergeChannels'}

    categories = []
    for cat in CATEGORIES:
        filter_names = get_filters_by_category(cat)
        filters = []
        for name in sorted(filter_names):
            # Skip multi-input combiners
            if name in SKIP_FILTERS:
                continue
            meta = get_filter_metadata(name)
            filters.append({
                'name': name,
                'description': meta.get('description', '')[:40],
            })
        # Only add category if it has filters
        if filters:
            categories.append({
                'name': cat.title(),
                'filters': filters,
            })
    return categories


def _to_snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    import re
    # Insert underscore before uppercase letters, then lowercase everything
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _get_param_range(name: str, default, param_type: str) -> tuple:
    """Infer slider range from parameter name."""
    name_lower = name.lower()

    # Handle non-numeric types
    if param_type in ('str', 'bool'):
        return (0, 1, 1)

    if name_lower in ('factor', 'opacity', 'scale'):
        return (0.0, 3.0, 0.1)
    elif name_lower in ('radius', 'sigma'):
        return (0.0, 20.0, 0.5)
    elif name_lower in ('threshold1', 'threshold2', 'value', 'threshold'):
        return (0, 255, 1)
    elif name_lower in ('k1', 'k2', 'k3', 'p1', 'p2'):
        return (-1.0, 1.0, 0.05)
    elif name_lower == 'angle':
        return (-180.0, 180.0, 5.0)
    elif name_lower in ('kernel_size', 'ksize', 'aperture_size'):
        return (1, 15, 2)
    elif name_lower in ('iterations',):
        return (1, 10, 1)
    elif param_type == 'int':
        try:
            return (0, max(100, int(default * 3) if default else 100), 1)
        except (TypeError, ValueError):
            return (0, 100, 1)
    else:
        try:
            return (0.0, max(10.0, float(default) * 3 if default else 10.0), 0.1)
        except (TypeError, ValueError):
            return (0.0, 10.0, 0.1)


class FilterDesigner(
    Element,
    component='filter_designer.js',
    dependencies=['vendor/drawflow.min.js'],
):
    """Node-based visual filter pipeline editor.

    A reusable component for building ImageStag filter pipelines visually.
    Uses Drawflow for the node graph editor.

    :param filters: List of filter definitions (auto-generated if not provided)
    :param categories: List of category definitions (auto-generated if not provided)
    :param on_graph_change: Callback when graph changes
    :param on_execute: Callback when user clicks execute
    :param show_source_node: Whether to show source node by default
    :param show_output_node: Whether to show output node by default
    """

    def __init__(
        self,
        *,
        filters: list[dict] | None = None,
        categories: list[dict] | None = None,
        on_graph_change: Callable[[dict], None] | None = None,
        on_node_selected: Callable[[dict], None] | None = None,
        on_execute: Callable[[dict], None] | None = None,
        on_notify: Callable[[dict], None] | None = None,
        on_export_requested: Callable[[dict], None] | None = None,
        on_import_completed: Callable[[dict], None] | None = None,
        show_source_node: bool = True,
        show_output_node: bool = True,
        source_images: list[str] | None = None,
        default_source_image: str = 'astronaut',
    ) -> None:
        super().__init__()

        # Add resources directory for JS/CSS files
        self.add_resource(Path(__file__).parent / 'vendor')
        self.add_resource(Path(__file__).parent)

        # Set props for Vue component
        self._props['filters'] = filters or get_filter_list()
        self._props['categories'] = categories or get_category_list()
        self._props['showSourceNode'] = show_source_node
        self._props['showOutputNode'] = show_output_node
        self._props['sourceImages'] = source_images or []
        self._props['defaultSourceImage'] = default_source_image

        # Store callbacks
        self._on_graph_change = on_graph_change
        self._on_node_selected = on_node_selected
        self._on_execute = on_execute
        self._on_notify = on_notify
        self._on_export_requested = on_export_requested
        self._on_import_completed = on_import_completed
        self._on_image_upload: Callable[[str, 'Image'], None] | None = None

        # Python-side graph state (single source of truth)
        self.graph = FilterGraph()
        self._id_to_name: dict[str, str] = {}  # Drawflow ID -> descriptive name
        self._name_counter: dict[str, int] = {}  # For unique name generation

        # Register event handlers - incremental updates
        self.on('node-added', self._handle_node_added)
        self.on('node-removed', self._handle_node_removed)
        self.on('connection-added', self._handle_connection_added)
        self.on('connection-removed', self._handle_connection_removed)
        self.on('param-changed', self._handle_param_changed)
        self.on('layout-changed', self._handle_layout_changed)
        # Other events
        self.on('execute', self._handle_execute)
        self.on('node-selected', self._handle_node_selected)
        self.on('image-uploaded', self._handle_image_upload)
        self.on('notify', self._handle_notify)
        self.on('export-requested', self._handle_export_requested)
        self.on('import-completed', self._handle_import_completed)
        self.on('preset-loaded', self._handle_preset_loaded)

    def _generate_name(self, node_type: str, filter_name: str | None = None) -> str:
        """Generate unique descriptive name for a node.

        :param node_type: 'source', 'output', 'filter', or 'combiner'
        :param filter_name: Filter class name (for filter nodes)
        :returns: Unique name like 'input', 'gaussian_blur', 'gaussian_blur_2', etc.
        """
        if node_type == 'source':
            base = 'input'
        elif node_type == 'output':
            base = 'output'
        elif filter_name:
            base = _to_snake_case(filter_name)
        else:
            base = 'node'

        count = self._name_counter.get(base, 0) + 1
        self._name_counter[base] = count
        return base if count == 1 else f"{base}_{count}"

    def _handle_node_added(self, e: GenericEventArguments) -> None:
        """Handle node added event from JavaScript."""
        data = e.args
        node_id = str(data.get('id'))
        node_type = data.get('type', 'filter')
        filter_name = data.get('filterName')
        x = data.get('x', 0)
        y = data.get('y', 0)
        source_image = data.get('sourceImage')

        # Generate descriptive name
        name = self._generate_name(node_type, filter_name)
        self._id_to_name[node_id] = name

        # Create GraphNode based on type
        if node_type == 'source':
            # Use PipelineSource for proper source handling
            source = PipelineSource.sample(source_image) if source_image else None
            node = GraphNode(name=name, source=source)
        elif node_type == 'output':
            node = GraphNode(name=name, is_output=True)
        elif filter_name:
            # Create filter instance with default params
            filter_cls = FILTER_REGISTRY.get(filter_name.lower()) or FILTER_REGISTRY.get(filter_name)
            if filter_cls:
                filter_instance = filter_cls()
                node = GraphNode(name=name, filter=filter_instance)
            else:
                node = GraphNode(name=name)
        else:
            node = GraphNode(name=name)

        # Add to graph
        self.graph.add_node(name, node, x, y)

        # Notify graph changed
        if self._on_graph_change:
            self._on_graph_change(self.graph.to_dict())

    def _handle_node_removed(self, e: GenericEventArguments) -> None:
        """Handle node removed event from JavaScript."""
        data = e.args
        node_id = str(data.get('id'))

        name = self._id_to_name.pop(node_id, None)
        if name:
            self.graph.remove_node(name)

            # Notify graph changed
            if self._on_graph_change:
                self._on_graph_change(self.graph.to_dict())

    def _handle_connection_added(self, e: GenericEventArguments) -> None:
        """Handle connection added event from JavaScript."""
        data = e.args
        from_id = str(data.get('fromNode'))
        to_id = str(data.get('toNode'))
        from_output = data.get('fromOutput', 0)
        to_input = data.get('toInput', 0)

        from_name = self._id_to_name.get(from_id)
        to_name = self._id_to_name.get(to_id)

        if from_name and to_name:
            # Convert port indices to port names
            from_port = 'output' if from_output == 0 else f'output_{from_output}'
            to_port = 'input' if to_input == 0 else f'input_{to_input}'
            conn = GraphConnection(
                from_node=from_name,
                to_node=to_name,
                from_port=from_port,
                to_port=to_port,
            )
            self.graph.add_connection(conn)

            # Notify graph changed
            if self._on_graph_change:
                self._on_graph_change(self.graph.to_dict())

    def _handle_connection_removed(self, e: GenericEventArguments) -> None:
        """Handle connection removed event from JavaScript."""
        data = e.args
        from_id = str(data.get('fromNode'))
        to_id = str(data.get('toNode'))
        from_output = data.get('fromOutput', 0)
        to_input = data.get('toInput', 0)

        from_name = self._id_to_name.get(from_id)
        to_name = self._id_to_name.get(to_id)

        if from_name and to_name:
            self.graph.remove_connection(from_name, to_name, from_output, to_input)

            # Notify graph changed
            if self._on_graph_change:
                self._on_graph_change(self.graph.to_dict())

    def _handle_param_changed(self, e: GenericEventArguments) -> None:
        """Handle parameter change from JavaScript."""
        data = e.args
        node_id = str(data.get('nodeId'))
        param_name = data.get('param')
        value = data.get('value')

        name = self._id_to_name.get(node_id)
        if name and param_name is not None:
            try:
                self.graph.update_param(name, param_name, value)
                # Notify graph changed
                if self._on_graph_change:
                    self._on_graph_change(self.graph.to_dict())
            except ValueError:
                pass  # Node or param doesn't exist

    def _handle_layout_changed(self, e: GenericEventArguments) -> None:
        """Handle node position change from JavaScript."""
        data = e.args
        node_id = str(data.get('nodeId'))
        x = data.get('x', 0)
        y = data.get('y', 0)

        name = self._id_to_name.get(node_id)
        if name:
            self.graph.update_layout(name, x, y)

    def _handle_execute(self, e: GenericEventArguments) -> None:
        """Handle execute button click."""
        # Pass the current graph state
        if self._on_execute:
            self._on_execute(self.graph.to_dict())
        elif self._on_graph_change:
            self._on_graph_change(self.graph.to_dict())

    def _handle_node_selected(self, e: GenericEventArguments) -> None:
        """Handle node selection."""
        if self._on_node_selected:
            self._on_node_selected(e.args)

    def _handle_image_upload(self, e: GenericEventArguments) -> None:
        """Handle image upload from source node."""
        if self._on_image_upload:
            self._on_image_upload(e.args)

    def _handle_notify(self, e: GenericEventArguments) -> None:
        """Handle notify events from JavaScript."""
        if self._on_notify:
            self._on_notify(e.args)

    def _handle_export_requested(self, e: GenericEventArguments) -> None:
        """Handle export request from JavaScript."""
        if self._on_export_requested:
            self._on_export_requested(e.args)

    def _handle_import_completed(self, e: GenericEventArguments) -> None:
        """Handle import completion from JavaScript."""
        if self._on_import_completed:
            self._on_import_completed(e.args)

    def _handle_preset_loaded(self, e: GenericEventArguments) -> None:
        """Handle preset-loaded event from JavaScript with ID mapping.

        This is called after loadPreset() completes in JS, providing
        the mapping from node names to Drawflow IDs.
        """
        data = e.args
        id_to_name = data.get('idToName', {})

        # Build reverse mapping: Drawflow ID -> node name
        self._id_to_name.clear()
        for name, drawflow_id in id_to_name.items():
            self._id_to_name[str(drawflow_id)] = name

        # Notify that the graph changed (triggers preview update)
        if self._on_graph_change:
            self._on_graph_change(self.graph.to_dict())

    def set_upload_handler(self, handler: Callable[[dict], None]) -> None:
        """Set handler for image uploads.

        Handler receives dict with 'nodeId', 'fileName', 'data' (base64).
        """
        self._on_image_upload = handler

    def notify_image_added(self, image_name: str) -> None:
        """Notify component that an uploaded image is available."""
        self.run_method('addUploadedImage', image_name)

    def set_output_image(self, src: str, info: str = '') -> None:
        """Set the output preview image.

        :param src: Base64 data URL or image path
        :param info: Info text to display (e.g., "512x512 | RGB")
        """
        self.run_method('setOutputImage', src, info)

    def set_output_images(self, images: list[dict]) -> None:
        """Set multiple output preview images for multi-output nodes.

        :param images: List of dicts with 'name', 'src', 'info' keys
        """
        self.run_method('setOutputImages', images)

    def get_graph_data(self) -> dict:
        """Get the current graph data from Python state.

        :returns: Graph dict with nodes, connections, and layout
        """
        return self.graph.to_dict()

    def clear_graph(self) -> None:
        """Clear all nodes from the graph."""
        # Reset Python state
        self.graph = FilterGraph()
        self._id_to_name.clear()
        self._name_counter.clear()
        # Clear JS visualization
        self.run_method('clearGraph')

    def load_graph(self, graph: 'FilterGraph') -> None:
        """Load a FilterGraph into the visual editor.

        Replaces the current graph state and updates the visualization.

        :param graph: FilterGraph instance to visualize
        """
        from imagestag.filters.graph import FilterGraph as FG

        if not isinstance(graph, FG):
            raise TypeError(f"Expected FilterGraph, got {type(graph).__name__}")

        # Reset state - ID mapping will be set by preset-loaded event
        self._id_to_name.clear()
        self._name_counter.clear()

        # Copy the graph
        self.graph = graph

        # Pre-populate name counter based on existing names
        # (so future node additions get correct names like 'gaussian_blur_2')
        for name in graph.nodes:
            base = name.rstrip('0123456789_')
            if base:
                self._name_counter[base] = self._name_counter.get(base, 0) + 1

        # Load into JS visualization - preset-loaded event will provide ID mapping
        self.run_method('loadPreset', graph.to_dict())

    @staticmethod
    def build_pipeline(graph_data: dict) -> FilterPipeline | FilterGraph | None:
        """Build a FilterPipeline or FilterGraph from graph data.

        :param graph_data: Dict with 'nodes' and 'connections' from the component
        :returns: FilterPipeline for linear graphs, FilterGraph for branching, or None
        """
        nodes = graph_data.get('nodes', {})
        connections = graph_data.get('connections', [])

        if not nodes:
            return None

        # Build adjacency lists
        incoming: dict[str, list[dict]] = {nid: [] for nid in nodes}
        outgoing: dict[str, list[dict]] = {nid: [] for nid in nodes}

        for conn in connections:
            from_node = str(conn['from_node'])
            to_node = str(conn['to_node'])
            if from_node in nodes and to_node in nodes:
                conn_info = {
                    'node': to_node,
                    'from_port': conn.get('from_port_name', 'output'),
                    'to_port': conn.get('to_port_name', 'input'),
                }
                outgoing[from_node].append(conn_info)
                incoming[to_node].append({
                    'node': from_node,
                    'from_port': conn.get('from_port_name', 'output'),
                    'to_port': conn.get('to_port_name', 'input'),
                })

        # Detect if graph has branching (multi-output or combiner nodes)
        has_combiner = any(n.get('type') == 'combiner' for n in nodes.values())
        has_multi_output = any(len(outgoing[nid]) > 1 for nid in nodes)

        if not has_combiner and not has_multi_output:
            # Build simple linear pipeline
            return FilterDesigner._build_linear_pipeline(nodes, incoming, outgoing)

        # Build FilterGraph for branching pipelines
        return FilterDesigner._build_filter_graph(nodes, incoming, outgoing, connections)

    @staticmethod
    def _build_linear_pipeline(
        nodes: dict,
        incoming: dict[str, list[dict]],
        outgoing: dict[str, list[dict]],
    ) -> FilterPipeline | None:
        """Build a simple linear pipeline."""
        pipeline = FilterPipeline()
        visited = set()
        current = None

        # Find the source node
        for nid, node in nodes.items():
            if node.get('type') == 'source':
                current = nid
                break

        # If no source, start from first filter with no incoming
        if not current:
            for nid, node in nodes.items():
                if node.get('type') == 'filter' and not incoming[nid]:
                    current = nid
                    break

        while current and current not in visited:
            visited.add(current)
            node = nodes[current]

            if node.get('type') == 'filter' and node.get('filterName'):
                filter_name = node['filterName']
                filter_cls = FILTER_REGISTRY.get(filter_name.lower()) or FILTER_REGISTRY.get(filter_name)

                if filter_cls:
                    params = {}
                    for p in node.get('params', []):
                        params[p['name']] = p['value']
                    pipeline.append(filter_cls(**params))

            # Move to next node
            next_conns = outgoing.get(current, [])
            current = next_conns[0]['node'] if next_conns else None

        return pipeline if pipeline.filters else None

    @staticmethod
    def _build_filter_graph(
        nodes: dict,
        incoming: dict[str, list[dict]],
        outgoing: dict[str, list[dict]],
        connections: list[dict],
    ) -> FilterGraph | None:
        """Build a FilterGraph for branching pipelines."""
        from imagestag.filters.graph import Blend, BlendMode

        graph = FilterGraph()

        # Find source node
        source_id = None
        for nid, node in nodes.items():
            if node.get('type') == 'source':
                source_id = nid
                break

        if not source_id:
            return None

        # Find combiner node (endpoint)
        combiner_id = None
        combiner_node = None
        for nid, node in nodes.items():
            if node.get('type') == 'combiner':
                combiner_id = nid
                combiner_node = node
                break

        # Trace branches from source through different paths
        # Each path to combiner becomes a branch

        def trace_branch(start_id: str, branch_name: str) -> list[Filter]:
            """Trace a branch from start to combiner/output, returning filters."""
            filters = []
            visited = set()
            current = start_id

            while current and current not in visited:
                visited.add(current)
                node = nodes.get(current)
                if not node:
                    break

                if node.get('type') == 'filter' and node.get('filterName'):
                    filter_name = node['filterName']
                    filter_cls = FILTER_REGISTRY.get(filter_name.lower()) or FILTER_REGISTRY.get(filter_name)

                    if filter_cls:
                        params = {}
                        for p in node.get('params', []):
                            params[p['name']] = p['value']
                        filters.append(filter_cls(**params))

                # Move to next (stop at combiner)
                next_conns = outgoing.get(current, [])
                if not next_conns:
                    break
                next_id = next_conns[0]['node']
                if nodes.get(next_id, {}).get('type') == 'combiner':
                    break
                current = next_id

            return filters

        # Get connections from source
        source_conns = outgoing.get(source_id, [])

        if len(source_conns) == 1:
            # Single path - check if it branches later
            # For now, just trace as single branch
            filters = trace_branch(source_conns[0]['node'], 'main')
            if filters:
                graph.branches['main'] = filters

        else:
            # Multiple paths from source
            for i, conn in enumerate(source_conns):
                branch_name = conn.get('from_port', f'branch_{i}')
                filters = trace_branch(conn['node'], branch_name)
                if filters:
                    graph.branches[branch_name] = filters

        # Set combiner as output
        if combiner_node:
            # Get input connections to combiner
            combiner_inputs = incoming.get(combiner_id, [])
            input_names = [c['node'] for c in combiner_inputs]

            # Map to branch names - for now use simple matching
            branch_names = list(graph.branches.keys())
            if len(branch_names) >= 2:
                mode = BlendMode.NORMAL
                if combiner_node.get('params'):
                    for p in combiner_node['params']:
                        if p['name'] == 'mode':
                            mode_str = p.get('value', 'NORMAL')
                            if hasattr(BlendMode, mode_str):
                                mode = BlendMode[mode_str]
                graph.output = Blend(inputs=branch_names[:2], mode=mode)

        return graph if graph.branches else None


# Re-export for convenience
__all__ = ['FilterDesigner', 'get_filter_list', 'get_category_list']
