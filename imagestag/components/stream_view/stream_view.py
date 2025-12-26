"""StreamView - High-performance video streaming component for NiceGUI.

A custom NiceGUI component for 1080p@60fps video streaming with multi-layer
compositing, per-layer FPS control, and SVG overlays.

Example:
    from imagestag.components.stream_view import StreamView, VideoStream

    video = VideoStream('video.mp4', loop=True)

    view = StreamView(width=1920, height=1080, show_metrics=True)
    view.add_layer(stream=video, fps=60, z_index=0)
    view.add_layer(url='/static/watermark.png', z_index=10)

    view.set_svg('''
        <circle cx="{x}" cy="{y}" r="20" fill="red"/>
    ''', {'x': 0, 'y': 0})

    @view.on_mouse_move
    def handle_mouse(e):
        view.update_svg_values(x=e.x, y=e.y)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from nicegui import app, run, ui
from nicegui.element import Element
from nicegui.events import GenericEventArguments, handle_event

from .layers import ImageStream, StreamViewLayer
from .metrics import FPSCounter, PythonMetrics

# Register static files for the component
_COMPONENT_DIR = Path(__file__).parent
_CSS_REGISTERED = False

if TYPE_CHECKING:
    from imagestag import Image
    from imagestag.filters import FilterPipeline


@dataclass
class Viewport:
    """Current viewport state (for zoom/pan).

    Coordinates are normalized to 0-1 range where (0,0) is top-left
    and (1,1) is bottom-right of the full source image.
    """

    x: float = 0.0  # Top-left X (0-1 normalized)
    y: float = 0.0  # Top-left Y (0-1 normalized)
    width: float = 1.0  # Viewport width (0-1 normalized, 1 = full)
    height: float = 1.0  # Viewport height (0-1 normalized, 1 = full)
    zoom: float = 1.0  # Zoom level (1 = no zoom)


@dataclass
class StreamViewMouseEventArguments(GenericEventArguments):
    """Mouse event arguments for StreamView component.

    Extends NiceGUI's GenericEventArguments with coordinates in three spaces:
    - Screen space (x, y): pixels on the display canvas
    - Source space (source_x, source_y): pixels in original source image
    - Normalized space (norm_x, norm_y): 0-1 range, resolution-independent
    """

    # Screen space (where user clicked on canvas)
    x: float = 0  # Display canvas X (0 to display_width)
    y: float = 0  # Display canvas Y (0 to display_height)

    # Source space (for depth=1.0 content layers)
    source_x: float = 0  # X in source image pixels
    source_y: float = 0  # Y in source image pixels

    # Normalized space (resolution-independent, 0-1 range)
    norm_x: float = 0  # 0-1 across source width
    norm_y: float = 0  # 0-1 across source height

    # Mouse button state
    buttons: int = 0
    alt: bool = False
    ctrl: bool = False
    shift: bool = False
    meta: bool = False

    # Viewport state
    viewport: Viewport | None = None


@dataclass
class StreamViewViewportEventArguments(GenericEventArguments):
    """Viewport change event arguments for StreamView component."""

    viewport: Viewport = None  # type: ignore
    prev_viewport: Viewport | None = None

    def __post_init__(self) -> None:
        if self.viewport is None:
            self.viewport = Viewport()


class StreamView(Element, component="stream_view.js"):
    """High-performance video streaming component with multi-layer compositing.

    Features:
    - Multiple image/video layers with independent FPS
    - Pull-based frame delivery with ahead-of-time buffering
    - SVG overlay with Python-controlled placeholders
    - Per-layer FilterPipeline support
    - Real-time performance metrics
    """

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        *,
        show_metrics: bool = False,
        # Zoom/pan configuration
        enable_zoom: bool = False,
        min_zoom: float = 1.0,
        max_zoom: float = 10.0,
        show_nav_window: bool = False,
        nav_window_position: str = "bottom-right",
        nav_window_size: tuple[int, int] = (160, 90),
    ) -> None:
        """Initialize StreamView component.

        :param width: Display width in pixels
        :param height: Display height in pixels
        :param show_metrics: Whether to show performance metrics overlay
        :param enable_zoom: Enable mouse wheel zoom and drag pan
        :param min_zoom: Minimum zoom level (1.0 = no zoom)
        :param max_zoom: Maximum zoom level
        :param show_nav_window: Show navigation thumbnail window when zoomed
        :param nav_window_position: Position of nav window ('top-left', 'top-right', 'bottom-left', 'bottom-right')
        :param nav_window_size: Size of nav window (width, height) in pixels
        """
        super().__init__()

        # Register CSS file once
        global _CSS_REGISTERED
        if not _CSS_REGISTERED:
            app.add_static_files('/stream_view', _COMPONENT_DIR)
            _CSS_REGISTERED = True

        # Add CSS to head
        ui.add_head_html('<link rel="stylesheet" href="/stream_view/stream_view.css">')

        # Component props
        self._props["width"] = width
        self._props["height"] = height
        self._props["showMetrics"] = show_metrics
        # Zoom/pan props
        self._props["enableZoom"] = enable_zoom
        self._props["minZoom"] = min_zoom
        self._props["maxZoom"] = max_zoom
        self._props["showNavWindow"] = show_nav_window
        self._props["navWindowPosition"] = nav_window_position
        self._props["navWindowWidth"] = nav_window_size[0]
        self._props["navWindowHeight"] = nav_window_size[1]

        # Store dimensions for viewport calculations
        self._width = width
        self._height = height

        # Layer management
        self._layers: dict[str, StreamViewLayer] = {}
        self._layer_order: list[str] = []  # Sorted by z_index

        # SVG overlay
        self._svg_template: str = ""
        self._svg_values: dict = {}

        # Viewport state (for zoom/pan - server-side cropping)
        self._viewport = Viewport()
        self._viewport_handler: Callable[[StreamViewViewportEventArguments], None] | None = None

        # Metrics
        self._metrics = PythonMetrics()
        self._fps_counter = FPSCounter()

        # Event handlers
        self._mouse_move_handler: Callable[[StreamViewMouseEventArguments], None] | None = None
        self._mouse_click_handler: Callable[[StreamViewMouseEventArguments], None] | None = None

        # Frame request handling
        self._pending_requests: dict[str, asyncio.Task] = {}

        # Register event handlers
        self.on("frame-request", self._handle_frame_request)
        self.on("mouse-move", self._handle_mouse_move)
        self.on("mouse-click", self._handle_mouse_click)
        self.on("viewport-change", self._handle_viewport_change)

        # Timer for checking pending frames
        self._timer = ui.timer(0.005, self._check_pending_frames)  # 200Hz check

    def add_layer(
        self,
        *,
        stream: ImageStream | None = None,
        stream_output: str | None = None,
        url: str | None = None,
        image: "Image | None" = None,
        fps: int = 60,
        z_index: int = 0,
        pipeline: "FilterPipeline | None" = None,
        buffer_size: int = 4,
        jpeg_quality: int = 85,
        use_png: bool = False,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
        piggyback: bool = False,
        depth: float = 1.0,
        overscan: int = 0,
    ) -> StreamViewLayer:
        """Add a layer to the StreamView.

        Exactly one of stream, url, or image must be provided (unless piggyback=True).

        :param stream: ImageStream for dynamic content
        :param stream_output: Output key for multi-output streams
        :param url: Static URL or data URL
        :param image: Static Image object
        :param fps: Target frames per second for this layer
        :param z_index: Stacking order (higher = on top)
        :param pipeline: Optional FilterPipeline to apply to frames
        :param buffer_size: Number of frames to buffer ahead
        :param jpeg_quality: JPEG encoding quality (1-100)
        :param use_png: Use PNG encoding for transparency support (slower)
        :param x: X position in pixels (None = 0)
        :param y: Y position in pixels (None = 0)
        :param width: Width in pixels (None = fill canvas)
        :param height: Height in pixels (None = fill canvas)
        :param piggyback: If True, layer receives frames via inject_frame() instead of
            having its own producer thread. Use for dependent layers that need zero-delay
            synchronization with a source stream.
        :param depth: Controls how layer responds to viewport zoom/pan:
            0.0 = fixed (HUD/overlays), 1.0 = content (default),
            <1.0 = parallax background, >1.0 = parallax foreground.
        :param overscan: Extra pixels around the displayed area for positioned layers.
            When moving, the "old" content includes this border to prevent showing
            stale content from previous position. Set to 0 to disable (default).
        :return: The created StreamViewLayer
        """
        layer = StreamViewLayer(
            z_index=z_index,
            target_fps=fps,
            pipeline=pipeline,
            stream=stream,
            stream_output=stream_output,
            url=url,
            image=image,
            buffer_size=buffer_size,
            jpeg_quality=jpeg_quality,
            use_png=use_png,
            x=x,
            y=y,
            width=width,
            height=height,
            piggyback=piggyback,
            depth=depth,
            overscan=overscan,
        )

        self._layers[layer.id] = layer
        self._update_layer_order()

        # Send layer config to JavaScript
        self._send_layer_config(layer)

        return layer

    def remove_layer(self, layer_id: str) -> None:
        """Remove a layer from the StreamView.

        :param layer_id: ID of the layer to remove
        """
        if layer_id in self._layers:
            layer = self._layers.pop(layer_id)
            layer.stop()
            self._update_layer_order()
            self.run_method("removeLayer", layer_id)

    def update_layer_position(
        self,
        layer_id: str,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Update a layer's position and size.

        :param layer_id: ID of the layer to update
        :param x: New X position (None to keep current)
        :param y: New Y position (None to keep current)
        :param width: New width (None to keep current)
        :param height: New height (None to keep current)
        """
        if layer_id in self._layers:
            layer = self._layers[layer_id]
            if x is not None:
                layer.x = x
            if y is not None:
                layer.y = y
            if width is not None:
                layer.width = width
            if height is not None:
                layer.height = height
            self.run_method("updateLayerPosition", layer_id, x, y, width, height)

    def _update_layer_order(self) -> None:
        """Update the layer order based on z_index."""
        self._layer_order = sorted(
            self._layers.keys(),
            key=lambda lid: self._layers[lid].z_index,
        )

    def _send_layer_config(self, layer: StreamViewLayer) -> None:
        """Send layer configuration to JavaScript."""
        config = {
            "id": layer.id,
            "z_index": layer.z_index,
            "target_fps": layer.target_fps,
            "is_static": layer.is_static,
            "source_type": layer.source_type,
            # Position/size (null means fill canvas)
            "x": layer.x,
            "y": layer.y,
            "width": layer.width,
            "height": layer.height,
            # Depth for viewport behavior (0=fixed, 1=content that zooms)
            "depth": layer.depth,
            # Overscan for positioned layers (extra border pixels)
            "overscan": layer.overscan,
        }

        # For static layers, send the content immediately
        if layer.is_static:
            config["static_content"] = layer.get_static_frame()

        self.run_method("addLayer", config)

    def set_svg(self, template: str, values: dict | None = None) -> None:
        """Set the SVG overlay template with placeholders.

        Placeholders use Python string format syntax: {placeholder_name}

        :param template: SVG template string with {placeholders}
        :param values: Initial placeholder values
        """
        self._svg_template = template
        self._svg_values = values or {}
        self._send_svg()

    def update_svg_values(self, **values) -> None:
        """Update SVG placeholder values.

        This is optimized for frequent updates (e.g., mouse tracking).

        :param values: Placeholder values to update
        """
        self._svg_values.update(values)
        self._send_svg()

    def _send_svg(self) -> None:
        """Send the rendered SVG to JavaScript."""
        try:
            rendered = self._svg_template.format(**self._svg_values)
            self.run_method("updateSvg", rendered)
        except KeyError:
            # Missing placeholder value, skip update
            pass

    def on_mouse_move(
        self, handler: Callable[[StreamViewMouseEventArguments], None]
    ) -> "StreamView":
        """Register a handler for mouse move events.

        :param handler: Callback receiving StreamViewMouseEventArguments
        :return: Self for method chaining
        """
        self._mouse_move_handler = handler
        return self

    def on_mouse_click(
        self, handler: Callable[[StreamViewMouseEventArguments], None]
    ) -> "StreamView":
        """Register a handler for mouse click events.

        :param handler: Callback receiving StreamViewMouseEventArguments
        :return: Self for method chaining
        """
        self._mouse_click_handler = handler
        return self

    def _handle_mouse_move(self, e: GenericEventArguments) -> None:
        """Handle mouse move event from JavaScript."""
        if self._mouse_move_handler:
            event = self._create_mouse_event(e)
            handle_event(self._mouse_move_handler, event)

    def _handle_mouse_click(self, e: GenericEventArguments) -> None:
        """Handle mouse click event from JavaScript."""
        if self._mouse_click_handler:
            event = self._create_mouse_event(e)
            handle_event(self._mouse_click_handler, event)

    def _create_mouse_event(self, e: GenericEventArguments) -> StreamViewMouseEventArguments:
        """Create mouse event from JavaScript event data."""
        args = e.args
        # Parse viewport if present
        viewport = None
        if "viewport" in args and args["viewport"]:
            vp = args["viewport"]
            viewport = Viewport(
                x=vp.get("x", 0),
                y=vp.get("y", 0),
                width=vp.get("width", 1),
                height=vp.get("height", 1),
                zoom=vp.get("zoom", 1),
            )

        return StreamViewMouseEventArguments(
            sender=self,
            client=self.client,
            args=args,
            x=args.get("x", 0),
            y=args.get("y", 0),
            source_x=args.get("sourceX", args.get("x", 0)),
            source_y=args.get("sourceY", args.get("y", 0)),
            buttons=args.get("buttons", 0),
            alt=args.get("alt", False),
            ctrl=args.get("ctrl", False),
            shift=args.get("shift", False),
            meta=args.get("meta", False),
            viewport=viewport,
        )

    # === Viewport/Zoom Methods ===

    def _handle_viewport_change(self, e: GenericEventArguments) -> None:
        """Handle viewport change event from JavaScript."""
        args = e.args
        prev_viewport = Viewport(
            x=self._viewport.x,
            y=self._viewport.y,
            width=self._viewport.width,
            height=self._viewport.height,
            zoom=self._viewport.zoom,
        )

        # Update viewport state
        self._viewport.x = args.get("x", 0)
        self._viewport.y = args.get("y", 0)
        self._viewport.width = args.get("width", 1)
        self._viewport.height = args.get("height", 1)
        self._viewport.zoom = args.get("zoom", 1)

        # Update all layers with new viewport
        for layer in self._layers.values():
            layer.set_viewport(self._viewport)

        # Call user handler if set
        if self._viewport_handler:
            event = StreamViewViewportEventArguments(
                sender=self,
                client=self.client,
                args=args,
                viewport=self._viewport,
                prev_viewport=prev_viewport,
            )
            handle_event(self._viewport_handler, event)

    def on_viewport_change(
        self, handler: Callable[[StreamViewViewportEventArguments], None]
    ) -> "StreamView":
        """Register a handler for viewport change events (zoom/pan).

        :param handler: Callback receiving StreamViewViewportEventArguments
        :return: Self for method chaining
        """
        self._viewport_handler = handler
        return self

    @property
    def viewport(self) -> Viewport:
        """Get current viewport state."""
        return self._viewport

    @property
    def zoom(self) -> float:
        """Get current zoom level."""
        return self._viewport.zoom

    def set_zoom(
        self,
        zoom: float,
        center_x: float | None = None,
        center_y: float | None = None,
    ) -> None:
        """Set zoom level programmatically.

        :param zoom: Zoom level (1.0 = no zoom)
        :param center_x: Optional X center point (0-1 normalized)
        :param center_y: Optional Y center point (0-1 normalized)
        """
        self.run_method("setZoom", zoom, center_x, center_y)

    def reset_zoom(self) -> None:
        """Reset zoom to 1x."""
        self.run_method("resetZoom")

    def _handle_frame_request(self, e: GenericEventArguments) -> None:
        """Handle frame request from JavaScript for a specific layer."""
        layer_id = e.args.get("layer_id")
        if not layer_id or layer_id not in self._layers:
            return

        layer = self._layers[layer_id]

        # Skip if static layer (content already sent)
        if layer.is_static:
            return

        # Check if we already have a pending request for this layer
        if layer_id in self._pending_requests:
            task = self._pending_requests[layer_id]
            if not task.done():
                return  # Still processing previous request

        # Try to get a buffered frame immediately
        frame_data = layer.get_buffered_frame()
        if frame_data is not None:
            timestamp, encoded, metadata = frame_data
            # Send frame with timing metadata
            self.run_method("updateLayer", layer_id, encoded, metadata.to_dict())
            self._fps_counter.tick()
            self._metrics.get_layer(layer_id).frames_delivered += 1
        else:
            # No buffered frame, start async production
            self._pending_requests[layer_id] = asyncio.create_task(
                self._produce_frame_async(layer)
            )

    async def _produce_frame_async(self, layer: StreamViewLayer) -> None:
        """Produce a frame asynchronously using run.io_bound."""
        if layer.stream is None:
            return

        try:
            # Run frame production in background thread
            frame_data = await run.io_bound(self._produce_frame_sync, layer)

            if frame_data is not None:
                _timestamp, encoded, metadata = frame_data
                self.run_method("updateLayer", layer.id, encoded, metadata.to_dict())
                self._fps_counter.tick()
                self._metrics.get_layer(layer.id).frames_delivered += 1

        except Exception:
            pass  # Ignore errors, JS will retry

        finally:
            # Clean up pending request
            self._pending_requests.pop(layer.id, None)

    @staticmethod
    def _produce_frame_sync(layer: StreamViewLayer) -> tuple[float, str, "FrameMetadata"] | None:
        """Produce a frame synchronously (runs in thread pool).

        This is a static method to avoid accessing instance state from thread.
        """
        import base64
        import time

        from .timing import FrameMetadata, new_frame_metadata

        if layer.stream is None:
            return None

        # Create metadata for timing tracking
        metadata = new_frame_metadata()

        # Get frame from stream
        timestamp = time.perf_counter()
        try:
            frame_result = layer.stream.get_frame(timestamp)
        except Exception:
            return None

        if frame_result is None:
            return None

        # Handle multi-output streams
        if isinstance(frame_result, dict):
            if layer.stream_output is None:
                frame = next(iter(frame_result.values()))
            else:
                frame = frame_result.get(layer.stream_output)
                if frame is None:
                    return None
        else:
            frame = frame_result

        # Apply filter pipeline if present
        if layer.pipeline is not None:
            try:
                for f in layer.pipeline.filters:
                    filter_start = FrameMetadata.now_ms()
                    frame = f.apply(frame)
                    filter_end = FrameMetadata.now_ms()
                    metadata.add_filter_timing(f.__class__.__name__, filter_start, filter_end)
            except Exception:
                pass

        # Encode to JPEG
        metadata.encode_start = FrameMetadata.now_ms()
        try:
            jpeg_bytes = frame.to_jpeg(quality=layer.jpeg_quality)
            if jpeg_bytes is None:
                return None
            encoded = base64.b64encode(jpeg_bytes).decode("ascii")
            metadata.encode_end = FrameMetadata.now_ms()
            metadata.send_time = FrameMetadata.now_ms()
            return (timestamp, encoded, metadata)
        except Exception:
            return None

    def _check_pending_frames(self) -> None:
        """Timer callback to check for completed frame production."""
        # Clean up completed tasks
        completed = [
            lid for lid, task in self._pending_requests.items() if task.done()
        ]
        for lid in completed:
            self._pending_requests.pop(lid, None)

    def start(self) -> None:
        """Start all layers."""
        for layer in self._layers.values():
            if not layer.is_static:
                layer.start()
        self.run_method("start")

    def stop(self) -> None:
        """Stop all layers."""
        for layer in self._layers.values():
            layer.stop()
        self.run_method("stop")

    def get_metrics(self) -> dict:
        """Get current performance metrics.

        :return: Dictionary of metrics for Python and all layers
        """
        # Update layer metrics
        for layer_id, layer in self._layers.items():
            metrics = self._metrics.get_layer(layer_id)
            metrics.buffer_depth = len(layer._frame_buffer)
            metrics.frames_produced = layer.frames_produced
            metrics.frames_dropped = layer.frames_dropped
            metrics.target_fps = layer.target_fps
            metrics.actual_fps = self._fps_counter.fps

        return self._metrics.to_dict()

    async def get_js_metrics(self) -> dict:
        """Get JavaScript-side performance metrics.

        :return: Dictionary of JS metrics
        """
        return await self.run_method("getMetrics")

    def _handle_delete(self) -> None:
        """Clean up when component is deleted."""
        self.stop()
        self._timer.deactivate()
        super()._handle_delete()
