"""Filter Explorer - Interactive filter testing with node-based pipeline builder.

A NiceGUI application for exploring ImageStag filters with a visual graph editor.
Uses the reusable FilterDesigner component for the node-based pipeline builder.
"""

from __future__ import annotations

import asyncio
import base64
import json
import uuid

from fastapi import Response
from nicegui import ui, app

from imagestag import Image, GeometryList, ImageList
from imagestag.skimage import SKImage
from imagestag import samples as imagestag_samples
from imagestag.filters import FilterContext, PipelineSource, ExecutionMode, GraphNode
from imagestag.components import FilterDesigner
from imagestag.tools.presets import PRESETS, get_preset_names

# Store pending exports for download
_pending_exports: dict[str, str] = {}


class FilterExplorerApp:
    """Main application class for the Filter Explorer."""

    def __init__(self):
        # Combine skimage and imagestag samples
        self.available_images = list(SKImage.list_images()) + imagestag_samples.list_images()
        self.custom_images: dict[str, Image] = {}  # Custom uploaded images
        self.default_image_name = 'stag'
        self.source_images: dict[str, Image] = {}  # Cache for loaded images
        self.designer: FilterDesigner | None = None
        self.upload_counter = 0

        # Store node results for selected node preview
        self.node_results: dict[str, Image | dict] = {}
        self.last_graph_data: dict | None = None
        self.selected_node_id: str | None = None
        self.preset_select: ui.select | None = None

    def _get_source_image(self, image_name: str) -> Image:
        """Get or load a source image by name."""
        # Check custom uploaded images first
        if image_name in self.custom_images:
            return self.custom_images[image_name]
        # Cache loaded images
        if image_name not in self.source_images:
            # Try imagestag samples first (group, stag), then skimage
            if image_name in imagestag_samples.list_images():
                self.source_images[image_name] = imagestag_samples.load(image_name)
            else:
                self.source_images[image_name] = SKImage.load(image_name)
        return self.source_images[image_name]

    def _handle_upload(self, upload_data: dict):
        """Handle image file upload from source node."""
        try:
            # Extract base64 data (remove data:image/...;base64, prefix)
            data_url = upload_data.get('data', '')
            if ',' in data_url:
                base64_data = data_url.split(',', 1)[1]
            else:
                base64_data = data_url

            import base64 as b64
            image_bytes = b64.b64decode(base64_data)
            img = Image(image_bytes)

            self.upload_counter += 1
            name = f'upload_{self.upload_counter}'
            self.custom_images[name] = img
            self.available_images.append(name)

            # Notify component that image is available
            if self.designer:
                self.designer.notify_image_added(name)

            ui.notify(f'Uploaded: {name} ({img.width}x{img.height})', type='positive')
        except Exception as ex:
            ui.notify(f'Failed to load image: {ex}', type='negative')

    def _on_graph_change(self, graph_data: dict):
        """Handle graph changes - execute pipeline and update preview."""
        self.last_graph_data = graph_data
        self._update_preview(graph_data)

    def _on_node_selected(self, event_data: dict):
        """Handle node selection - update sidebar preview with node's output."""
        node_id = str(event_data.get('id', ''))
        # Translate Drawflow ID to node name using designer's mapping
        if self.designer:
            node_name = self.designer._id_to_name.get(node_id, node_id)
        else:
            node_name = node_id
        self.selected_node_id = node_name

        # Re-execute graph to ensure we have fresh results
        if self.last_graph_data:
            self._update_preview(self.last_graph_data)
        else:
            # Update sidebar with selected node's output
            self._update_sidebar_preview(node_name)

    def _load_preset(self, preset_key: str):
        """Load a preset graph configuration via FilterGraph."""
        if not preset_key or not self.designer:
            return

        preset = PRESETS.get(preset_key)
        if preset:
            # Parse preset through FilterGraph for validation
            from imagestag.filters import FilterGraph
            graph = FilterGraph.from_dict(preset)
            # Clear selection so output node is shown automatically
            self.selected_node_id = None
            # Load via FilterGraph (goes through to_dict() -> loadPreset)
            self.designer.load_graph(graph)
            # Reset the select to show placeholder
            if self.preset_select:
                self.preset_select.value = None

    def _on_notify(self, event_data: dict):
        """Handle notify events from FilterDesigner."""
        message = event_data.get('message', '')
        msg_type = event_data.get('type', 'info')
        ui.notify(message, type=msg_type)

    def _on_export_requested(self, _event_data: dict):
        """Handle export request - show filename dialog and trigger download."""
        # Get export data from Python-side graph state (single source of truth)
        export_data = self.designer.get_graph_data()

        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('Export Pipeline').classes('text-lg font-bold mb-2')
            filename_input = ui.input(
                'Filename',
                value='pipeline.json',
                placeholder='Enter filename'
            ).classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close).props('flat')

                def do_export():
                    filename = filename_input.value
                    if not filename.endswith('.json'):
                        filename += '.json'

                    # Generate unique ID for this download
                    export_id = str(uuid.uuid4())
                    json_data = json.dumps(export_data, indent=2)
                    _pending_exports[export_id] = json_data

                    # Trigger download via JavaScript
                    ui.run_javascript(f'''
                        const a = document.createElement('a');
                        a.href = '/api/download/{export_id}?filename=' + encodeURIComponent('{filename}');
                        a.download = '{filename}';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                    ''')
                    dialog.close()
                    ui.notify(f'Downloading {filename}', type='positive')

                ui.button('Export', on_click=do_export).props('color=primary')

        dialog.open()

    def _on_import_completed(self, result: dict):
        """Handle import completion notification."""
        if result.get('success'):
            ui.notify(f"Imported {result.get('filename', 'pipeline')}", type='positive')
        else:
            ui.notify(f"Import failed: {result.get('error', 'Unknown error')}", type='negative')

    def _get_all_sources(self, graph_data: dict) -> dict[str, Image]:
        """Get all source images from graph data, keyed by node ID.

        Uses PipelineSource for unified source handling. Supports:
        - Explicit format: {'class': 'PipelineSource', 'type': 'SAMPLE', 'value': 'coins'}
        - Custom uploaded images
        """
        sources = {}
        nodes = graph_data.get('nodes', {})

        for node_id, node_data in nodes.items():
            pipeline_source = None

            # Explicit PipelineSource format
            if node_data.get('class') == 'PipelineSource':
                graph_node = GraphNode.from_dict(str(node_id), node_data)
                pipeline_source = graph_node.get_source()

            # Load the source if found
            if pipeline_source:
                # Check for custom uploaded images first
                if pipeline_source.is_sample:
                    image_name = pipeline_source.value
                    if image_name in self.custom_images:
                        sources[str(node_id)] = self.custom_images[image_name]
                        continue

                # Load via PipelineSource (designer mode = load samples)
                img = pipeline_source.load(mode=ExecutionMode.DESIGNER)
                if img:
                    sources[str(node_id)] = img

        return sources

    def _execute_graph(self, graph_data: dict) -> Image | dict | None:
        """Execute the graph with proper multi-source support."""
        from imagestag.filters import FILTER_REGISTRY
        from imagestag.filters.graph import Blend, BlendMode

        nodes = graph_data.get('nodes', {})
        connections = graph_data.get('connections', [])

        if not nodes:
            return None

        # Get all source images
        sources = self._get_all_sources(graph_data)
        if not sources:
            return None

        # Build adjacency lists
        outgoing: dict[str, list[dict]] = {nid: [] for nid in nodes}
        incoming: dict[str, list[dict]] = {nid: [] for nid in nodes}

        for conn in connections:
            # Parse connection format:
            # New format: {"from": "node" or ["node", "port"], "to": "node" or ["node", "port"]}
            # Legacy format: {"from_node": ..., "to_node": ..., "from_output": 0, "to_input": 1}
            if 'from' in conn:
                # New format
                from_part = conn['from']
                to_part = conn['to']
                if isinstance(from_part, list):
                    from_node, from_port = str(from_part[0]), from_part[1]
                else:
                    from_node, from_port = str(from_part), 'output'
                if isinstance(to_part, list):
                    to_node, to_port = str(to_part[0]), to_part[1]
                else:
                    to_node, to_port = str(to_part), 'input'
            else:
                # Legacy format
                from_node = str(conn['from_node'])
                to_node = str(conn['to_node'])
                # Handle both port name formats:
                # Old format: from_port_name, to_port_name (strings)
                # FilterGraph format: from_output, to_input (integers)
                from_port = conn.get('from_port_name')
                to_port = conn.get('to_port_name')
                if from_port is None:
                    # Convert integer index to port name using source filter's _output_ports
                    from_idx = conn.get('from_output', 0)
                    source_node = nodes.get(from_node, {})
                    source_filter_name = source_node.get('filterName') or source_node.get('class')
                    if source_filter_name:
                        source_filter_cls = FILTER_REGISTRY.get(source_filter_name.lower()) or FILTER_REGISTRY.get(source_filter_name)
                        if source_filter_cls and getattr(source_filter_cls, '_output_ports', None) and from_idx < len(source_filter_cls._output_ports):
                            from_port = source_filter_cls._output_ports[from_idx]['name']
                        else:
                            from_port = f'output_{from_idx}' if from_idx > 0 else 'output'
                    else:
                        from_port = f'output_{from_idx}' if from_idx > 0 else 'output'
                if to_port is None:
                    to_idx = conn.get('to_input', 0)
                    # Get port name from target node's filter class if available
                    target_node = nodes.get(to_node, {})
                    filter_name = target_node.get('filterName') or target_node.get('class')
                    if filter_name:
                        filter_cls = FILTER_REGISTRY.get(filter_name.lower()) or FILTER_REGISTRY.get(filter_name)
                        if filter_cls and getattr(filter_cls, '_input_ports', None) and to_idx < len(filter_cls._input_ports):
                            to_port = filter_cls._input_ports[to_idx]['name']
                        else:
                            to_port = f'input_{to_idx}' if to_idx > 0 else 'input'
                    else:
                        to_port = f'input_{to_idx}' if to_idx > 0 else 'input'

            if from_node in nodes and to_node in nodes:
                outgoing[from_node].append({
                    'node': to_node,
                    'from_port': from_port,
                    'to_port': to_port,
                })
                incoming[to_node].append({
                    'node': from_node,
                    'from_port': from_port,
                    'to_port': to_port,
                })

        # Execute nodes in topological order
        # Store results for each node
        node_results: dict[str, Image | dict] = {}

        # Initialize source nodes with their images
        for node_id, image in sources.items():
            node_results[node_id] = image.copy()

        # Find execution order (simple: process nodes with all inputs ready)
        processed = set(sources.keys())
        to_process = [nid for nid in nodes if nid not in processed]

        max_iterations = len(nodes) * 2
        iteration = 0
        while to_process and iteration < max_iterations:
            iteration += 1
            for node_id in list(to_process):
                node = nodes[node_id]
                inc = incoming.get(node_id, [])

                # Check if all inputs are ready (use string keys)
                if all(str(c['node']) in processed for c in inc):
                    # Execute this node - detect type from explicit class format
                    # Check class first (PipelineOutput has "type": "IMAGE" which would conflict)
                    if node.get('class') == 'PipelineSource':
                        node_type = 'source'
                    elif node.get('class') == 'PipelineOutput':
                        node_type = 'output'
                    elif 'class' in node:
                        # Check if it's a combiner based on filter metadata
                        filter_name = node.get('class', '')
                        filter_cls = FILTER_REGISTRY.get(filter_name.lower()) or FILTER_REGISTRY.get(filter_name)
                        if filter_cls and getattr(filter_cls, '_input_ports', None) and len(filter_cls._input_ports) > 1:
                            node_type = 'combiner'
                        else:
                            node_type = 'filter'
                    else:
                        # Unknown node type
                        node_type = None

                    if node_type == 'filter':
                        # Single input filter (or generator with no input)
                        filter_name = node.get('filterName') or node.get('class')
                        filter_cls = FILTER_REGISTRY.get(filter_name.lower()) or FILTER_REGISTRY.get(filter_name)

                        # Get input image if there are incoming connections
                        input_image = None
                        if inc:
                            input_key = str(inc[0]['node'])
                            input_image = node_results.get(input_key)
                            if input_image is not None:
                                # Handle dict inputs (take first)
                                if isinstance(input_image, dict):
                                    port_name = inc[0].get('from_port', 'output')
                                    if port_name in input_image:
                                        input_image = input_image[port_name]
                                    else:
                                        input_image = next(iter(input_image.values()))

                        if filter_cls:
                            # Extract params - handle both formats
                            node_params = node.get('params', {})
                            if isinstance(node_params, list):
                                # Old format: [{'name': 'sigma', 'value': 2.0}]
                                params = {p['name']: p['value'] for p in node_params}
                            else:
                                # FilterGraph format: {'sigma': 2.0}
                                params = dict(node_params) if node_params else {}
                            try:
                                filt = filter_cls(**params)
                                # Use __call__ which auto-handles ImageList
                                result = filt(input_image)  # input_image can be None for generators
                                node_results[node_id] = result
                            except Exception as e:
                                import traceback
                                traceback.print_exc()
                                node_results[node_id] = input_image
                        else:
                            node_results[node_id] = input_image

                    elif node_type == 'combiner':
                        # Multi-input combiner (Blend, SizeMatcher, etc.)
                        filter_name = node.get('filterName') or node.get('class', '')

                        # Build input images dict by port name
                        input_images = {}
                        for conn in inc:
                            to_port = conn.get('to_port', 'input')
                            from_node = str(conn['node'])
                            img = node_results.get(from_node)

                            # Handle dict outputs (multi-output filters)
                            if isinstance(img, dict):
                                from_port = conn.get('from_port', 'output')
                                if from_port in img:
                                    img = img[from_port]
                                else:
                                    img = next(iter(img.values())) if img else None

                            if img is not None:
                                input_images[to_port] = img

                        if len(input_images) >= 2:
                            # Get filter class and params
                            filter_cls = FILTER_REGISTRY.get(filter_name.lower()) or FILTER_REGISTRY.get(filter_name)

                            if filter_cls:
                                # Build params from node - handle both formats
                                node_params = node.get('params', {})
                                params = {}
                                if isinstance(node_params, list):
                                    # Old format: [{'name': 'mode', 'value': 'NORMAL'}]
                                    for p in node_params:
                                        param_name = p['name']
                                        # Skip deprecated params
                                        if param_name == 'use_geometry_styles':
                                            continue
                                        val = p.get('value')
                                        params[param_name] = val
                                else:
                                    # FilterGraph format: {'mode': 'NORMAL'}
                                    params = dict(node_params) if node_params else {}

                                # Build input names list from port connections or filter metadata
                                input_ports = node.get('inputPorts', [])
                                if input_ports:
                                    input_names = [port.get('name', f'input_{i}') for i, port in enumerate(input_ports)]
                                elif getattr(filter_cls, '_input_ports', None):
                                    # FilterGraph format: get port names from filter class
                                    input_names = [p['name'] for p in filter_cls._input_ports]
                                else:
                                    input_names = list(input_images.keys())

                                try:
                                    combiner = filter_cls(inputs=input_names, **params)
                                    result = combiner.apply_multi(input_images)
                                    node_results[node_id] = result
                                except Exception as e:
                                    import traceback
                                    traceback.print_exc()
                                    # Fallback: return first input
                                    node_results[node_id] = next(iter(input_images.values())) if input_images else None
                            else:
                                # Unknown filter, return first input
                                node_results[node_id] = next(iter(input_images.values())) if input_images else None
                        elif len(input_images) == 1:
                            node_results[node_id] = next(iter(input_images.values()))
                        else:
                            node_results[node_id] = None

                    elif node_type == 'output':
                        # Output just passes through
                        if inc:
                            source_node = str(inc[0]['node'])
                            result = node_results.get(source_node)
                            if isinstance(result, dict):
                                port_name = inc[0].get('from_port', 'output')
                                if port_name in result:
                                    result = result[port_name]
                                else:
                                    result = next(iter(result.values()))
                            node_results[node_id] = result
                        else:
                            node_results[node_id] = None

                    processed.add(node_id)
                    to_process.remove(node_id)

        # Store all node results for selected node preview
        self.node_results = node_results

        # Find output node result
        for node_id, node in nodes.items():
            if node.get('class') == 'PipelineOutput':
                # Check if output node has any incoming connections
                if not incoming.get(node_id):
                    # Output node is not connected - return None
                    return None
                result = node_results.get(node_id)
                # If result is None, the connection chain is broken
                if result is None:
                    return None
                return result

        # If no output node, return last processed result
        if node_results:
            return list(node_results.values())[-1]

        return None

    def _image_to_base64(self, img: Image) -> tuple[str, str]:
        """Convert image to base64 and info string."""
        png_data = img.to_png()
        base64_str = f'data:image/png;base64,{base64.b64encode(png_data).decode()}'
        info = f'{img.width}x{img.height} | {img.pixel_format.name}'
        return base64_str, info

    def _update_sidebar_preview(self, node_id: str | None):
        """Update sidebar preview with a specific node's output."""
        if not self.designer:
            return

        # Get the result for the selected node
        result = None
        node_name = 'No selection'

        if node_id and node_id in self.node_results:
            result = self.node_results.get(node_id)
            # Get node name from graph data
            if self.last_graph_data:
                node = self.last_graph_data.get('nodes', {}).get(node_id)
                if node:
                    node_name = node.get('name', node.get('filterName', node.get('type', 'Node')))

        if result is None:
            # No result for this node yet, show placeholder
            self.designer.set_output_image('', f'{node_name}: No output')
            return

        # Handle GeometryList - render as preview image
        if isinstance(result, GeometryList):
            preview = result.to_preview_image()
            out_base64, _ = self._image_to_base64(preview)
            info = f'{node_name}: {result.width}x{result.height} | {len(result)} geometries'
            self.designer.set_output_image(out_base64, info)
            return

        # Handle ImageList (from ExtractRegions) - show first image
        if isinstance(result, ImageList):
            if result:
                first_img = result.first()
                out_base64, _ = self._image_to_base64(first_img)
                info = f'{node_name}: {len(result)} regions | showing first'
                self.designer.set_output_image(out_base64, info)
            else:
                self.designer.set_output_image('', f'{node_name}: Empty ImageList')
            return

        # Handle list of images (legacy)
        if isinstance(result, list) and result and isinstance(result[0], Image):
            images = []
            for i, img in enumerate(result):
                img_base64, _ = self._image_to_base64(img)
                info = f'{img.width}x{img.height} | {img.pixel_format.name}'
                images.append({
                    'name': f'{node_name}: Region {i}',
                    'src': img_base64,
                    'info': info,
                })
            self.designer.set_output_images(images)
            return

        # Handle multi-output filters (dict of images/geometry)
        if isinstance(result, dict):
            if result:
                # Show ALL outputs in sidebar
                images = []
                for port_name, item in result.items():
                    if isinstance(item, GeometryList):
                        # Render geometry as preview
                        preview = item.to_preview_image()
                        img_base64, _ = self._image_to_base64(preview)
                        info = f'{item.width}x{item.height} | {len(item)} geometries'
                    elif isinstance(item, ImageList):
                        # Show first region as preview for ImageList
                        if item:
                            img_base64, _ = self._image_to_base64(item.first())
                            info = f'{len(item)} regions'
                        else:
                            continue
                    elif isinstance(item, list) and item and isinstance(item[0], Image):
                        # Show first region as preview for legacy image lists
                        img_base64, _ = self._image_to_base64(item[0])
                        info = f'{len(item)} regions'
                    elif isinstance(item, Image):
                        img_base64, _ = self._image_to_base64(item)
                        info = f'{item.width}x{item.height} | {item.pixel_format.name}'
                    else:
                        continue
                    images.append({
                        'name': f'{node_name}: {port_name}',
                        'src': img_base64,
                        'info': info,
                    })
                if images:
                    self.designer.set_output_images(images)
                else:
                    self.designer.set_output_image('', f'{node_name}: Empty output')
            else:
                self.designer.set_output_image('', f'{node_name}: Empty output')
            return

        # Single Image output
        if isinstance(result, Image):
            out_base64, _ = self._image_to_base64(result)
            info = f'{node_name}: {result.width}x{result.height} | {result.pixel_format.name}'
            self.designer.set_output_image(out_base64, info)
        else:
            self.designer.set_output_image('', f'{node_name}: Unknown output type')

    def _update_preview(self, graph_data: dict | None = None):
        """Execute the pipeline and update sidebar preview."""
        try:
            # Execute graph
            if graph_data:
                self._execute_graph(graph_data)
            else:
                self.node_results = {}  # Clear results when no graph

            # Update sidebar with selected node's output (or output node if none selected)
            if self.selected_node_id:
                self._update_sidebar_preview(self.selected_node_id)
            elif graph_data:
                # Find output node and use that
                output_nid = None
                source_nid = None
                for nid, node in graph_data.get('nodes', {}).items():
                    if node.get('class') == 'PipelineOutput':
                        output_nid = str(nid)
                    # Track first source node as fallback
                    elif node.get('class') == 'PipelineSource' and source_nid is None:
                        source_nid = str(nid)

                # Use output node if it has a result, otherwise fall back to source
                if output_nid and self.node_results.get(output_nid) is not None:
                    self._update_sidebar_preview(output_nid)
                elif source_nid and self.node_results.get(source_nid) is not None:
                    # Output has no result, show source as fallback
                    self._update_sidebar_preview(source_nid)
                elif output_nid:
                    # No results anywhere, show output status
                    self._update_sidebar_preview(output_nid)
                else:
                    if self.designer:
                        self.designer.set_output_image('', 'No output node')
            else:
                if self.designer:
                    self.designer.set_output_image('', 'No graph')

        except Exception as e:
            import traceback
            traceback.print_exc()
            ui.notify(f'Error: {e}', type='negative')

    def render(self):
        """Render the application."""
        # Header with source selector
        with ui.header().classes('bg-gray-900 items-center justify-between px-4'):
            with ui.row().classes('items-center gap-4'):
                ui.icon('auto_fix_high').classes('text-2xl text-blue-400')
                ui.label('Filter Explorer').classes('text-xl font-bold text-white')

            with ui.row().classes('items-center gap-4'):
                # Preset selector
                ui.label('Load Preset:').classes('text-gray-400')
                preset_options = {key: preset['name'] for key, preset in PRESETS.items()}
                self.preset_select = ui.select(
                    options=preset_options,
                    value=None,
                    on_change=lambda e: self._load_preset(e.value)
                ).props('dense dark outlined clearable').classes('w-48')

        # FilterDesigner fills full height below header (header is ~52px)
        with ui.element('div').classes('w-full').style('height: calc(100vh - 52px); overflow: hidden'):
            self.designer = FilterDesigner(
                on_graph_change=self._on_graph_change,
                on_node_selected=self._on_node_selected,
                on_notify=self._on_notify,
                on_export_requested=self._on_export_requested,
                on_import_completed=self._on_import_completed,
                show_source_node=True,
                show_output_node=True,
                source_images=self.available_images,
                default_source_image=self.default_image_name,
            )
            # Set upload handler for source nodes
            self.designer.set_upload_handler(self._handle_upload)


@app.get('/api/download/{export_id}')
async def download_pipeline(export_id: str, filename: str = 'pipeline.json'):
    """FastAPI endpoint to download pipeline JSON."""
    json_data = _pending_exports.pop(export_id, None)
    if json_data is None:
        return Response(content='Export not found', status_code=404)

    return Response(
        content=json_data,
        media_type='application/json',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


@ui.page('/')
def index(pipeline: str = None):
    """Main application page.

    :param pipeline: Optional base64-encoded pipeline to load from URL query param.
    """
    # Remove default body margin/padding
    ui.add_head_html('<style>body { margin: 0; padding: 0; overflow: hidden; }</style>')
    filter_app = FilterExplorerApp()
    filter_app.render()

    # Load pipeline from query param if provided
    if pipeline and filter_app.designer:
        async def load_pipeline():
            # Wait a bit for the component to be ready
            await asyncio.sleep(0.2)
            filter_app.designer.run_method('importFromString', pipeline)
            ui.notify('Loaded pipeline from URL', type='info')
        asyncio.create_task(load_pipeline())


def main():
    """Run the Filter Explorer application."""
    ui.run(
        title='Filter Explorer',
        show=False,
        reload=True,
        uvicorn_reload_includes='*.py,*.js,*.css',
    )


if __name__ in {'__main__', '__mp_main__'}:
    main()
