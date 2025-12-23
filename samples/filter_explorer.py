"""Filter Explorer - Interactive filter testing with node-based pipeline builder.

A NiceGUI application for exploring ImageStag filters with a visual graph editor.
Uses the reusable FilterDesigner component for the node-based pipeline builder.
"""

from __future__ import annotations

import base64

from nicegui import ui

from imagestag import Image, GeometryList, ImageList
from imagestag.skimage import SKImage
from imagestag import samples as imagestag_samples
from imagestag.filters import FilterContext

from components import FilterDesigner
from presets import PRESETS, get_preset_names


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
        self.selected_node_id = node_id

        # Re-execute graph to ensure we have fresh results
        if self.last_graph_data:
            self._update_preview(self.last_graph_data)
        else:
            # Update sidebar with selected node's output
            self._update_sidebar_preview(node_id)

    def _load_preset(self, preset_key: str):
        """Load a preset graph configuration."""
        if not preset_key or not self.designer:
            return

        preset = PRESETS.get(preset_key)
        if preset:
            # Call the JavaScript loadPreset method
            self.designer.run_method('loadPreset', preset)
            # Reset the select to show placeholder
            if self.preset_select:
                self.preset_select.value = None

    def _get_all_sources(self, graph_data: dict) -> dict[str, Image]:
        """Get all source images from graph data, keyed by node ID."""
        sources = {}
        nodes = graph_data.get('nodes', {})
        for node_id, node in nodes.items():
            if node.get('type') == 'source':
                image_name = self.default_image_name
                params = node.get('params', [])
                for param in params:
                    if param.get('name') == 'image':
                        val = param.get('value')
                        if val:
                            image_name = val
                        break
                sources[str(node_id)] = self._get_source_image(image_name)
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
            from_node = str(conn['from_node'])
            to_node = str(conn['to_node'])
            if from_node in nodes and to_node in nodes:
                outgoing[from_node].append({
                    'node': to_node,
                    'from_port': conn.get('from_port_name', 'output'),
                    'to_port': conn.get('to_port_name', 'input'),
                })
                incoming[to_node].append({
                    'node': from_node,
                    'from_port': conn.get('from_port_name', 'output'),
                    'to_port': conn.get('to_port_name', 'input'),
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
                    # Execute this node
                    node_type = node.get('type')

                    if node_type == 'filter':
                        # Single input filter (or generator with no input)
                        filter_name = node.get('filterName')
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
                            params = {}
                            for p in node.get('params', []):
                                params[p['name']] = p['value']
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
                        filter_name = node.get('filterName', '')

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
                                # Build params from node
                                params = {}
                                for p in node.get('params', []):
                                    param_name = p['name']
                                    # Skip deprecated params
                                    if param_name == 'use_geometry_styles':
                                        continue
                                    val = p.get('value')
                                    # Handle enum values (stored as strings)
                                    if p.get('type') == 'select' and val:
                                        params[param_name] = val
                                    else:
                                        params[param_name] = val

                                # Build input names list from port connections
                                input_ports = node.get('inputPorts', [])
                                input_names = [port.get('name', f'input_{i}') for i, port in enumerate(input_ports)]

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
                            result = node_results.get(str(inc[0]['node']))
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
            if node.get('type') == 'output':
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
                for nid, node in graph_data.get('nodes', {}).items():
                    if node.get('type') == 'output':
                        self._update_sidebar_preview(str(nid))
                        break
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
                show_source_node=True,
                show_output_node=True,
                source_images=self.available_images,
                default_source_image=self.default_image_name,
            )
            # Set upload handler for source nodes
            self.designer.set_upload_handler(self._handle_upload)


@ui.page('/')
def index():
    """Main application page."""
    # Remove default body margin/padding
    ui.add_head_html('<style>body { margin: 0; padding: 0; overflow: hidden; }</style>')
    app = FilterExplorerApp()
    app.render()


if __name__ in {'__main__', '__mp_main__'}:
    ui.run(
        title='Filter Explorer',
        show=False,
        reload=True,
        uvicorn_reload_includes='*.py,*.js,*.css',
    )
