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
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

logger = logging.getLogger(__name__)

from nicegui import app, run, ui
from nicegui.element import Element
from nicegui.events import GenericEventArguments, handle_event

from .layers import ImageStream, StreamViewLayer, VideoStream
from .metrics import FPSCounter, PythonMetrics

# WebRTC support (optional)
try:
    from .webrtc import WebRTCManager, WebRTCLayerConfig, AIORTC_AVAILABLE
except ImportError:
    WebRTCManager = None
    WebRTCLayerConfig = None
    AIORTC_AVAILABLE = False

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
        self.on("size-changed", self._handle_size_changed)

        # WebRTC support (optional)
        self._webrtc_manager: WebRTCManager | None = None
        self._webrtc_layers: dict[str, WebRTCLayerConfig] = {}
        self._pending_webrtc_offers: dict[str, dict] = {}  # layer_id -> offer dict
        self._pending_webrtc_configs: dict[str, WebRTCLayerConfig] = {}  # waiting for JS ready
        self._component_ready = False
        if AIORTC_AVAILABLE:
            self.on("webrtc-answer", self._handle_webrtc_answer)
        self.on("component-ready", self._handle_component_ready)

        # Timer for checking pending frames
        self._timer = ui.timer(0.005, self._check_pending_frames)  # 200Hz check
        # Timer for sending pending WebRTC offers (avoids stale client issues)
        self._webrtc_timer = ui.timer(0.1, self._send_pending_webrtc_offers)
        # Also schedule a one-shot delayed start for WebRTC
        ui.timer(0.5, self._start_pending_webrtc, once=True)

    def add_layer(
        self,
        *,
        stream: ImageStream | None = None,
        stream_output: str | None = None,
        url: str | None = None,
        image: "Image | None" = None,
        source_layer: "StreamViewLayer | str | None" = None,
        mask: "Image | str | None" = None,
        name: str = "",
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
        fullscreen_scale: str = "video",
    ) -> StreamViewLayer:
        """Add a layer to the StreamView.

        Exactly one of stream, url, image, or source_layer must be provided
        (unless piggyback=True).

        :param stream: ImageStream for dynamic content
        :param stream_output: Output key for multi-output streams
        :param url: Static URL or data URL
        :param image: Static Image object
        :param source_layer: Another layer to read frames from. The derived layer will
            automatically subscribe to the source layer's frames and process them.
            Can be a StreamViewLayer object or layer ID string.
        :param mask: Grayscale mask Image (or data URL) to apply to this layer.
            White = fully visible, black = transparent. Sent once to client.
        :param name: User-friendly display name for metrics overlay
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
        :param fullscreen_scale: Controls layer resolution in fullscreen mode:
            "video" = Match video resolution (e.g., 1920x1080 stays 1920x1080)
            "screen" = Render at screen resolution for sharper lines (best for PNG overlays)
        :return: The created StreamViewLayer
        """
        # Resolve source_layer if it's a string (layer ID)
        resolved_source_layer: StreamViewLayer | None = None
        if source_layer is not None:
            if isinstance(source_layer, str):
                if source_layer not in self._layers:
                    raise ValueError(f"Source layer '{source_layer}' not found")
                resolved_source_layer = self._layers[source_layer]
            else:
                resolved_source_layer = source_layer

        layer = StreamViewLayer(
            name=name,
            z_index=z_index,
            target_fps=fps,
            pipeline=pipeline,
            stream=stream,
            stream_output=stream_output,
            url=url,
            image=image,
            source_layer=resolved_source_layer,
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
            fullscreen_scale=fullscreen_scale,
        )

        self._layers[layer.id] = layer
        self._update_layer_order()

        # Set target size for frame resizing (reduces bandwidth)
        # Positioned layers use their explicit size, full-canvas layers use view size
        target_w = width if width is not None else self._width
        target_h = height if height is not None else self._height
        layer.set_target_size(target_w, target_h)

        # Send layer config to JavaScript
        self._send_layer_config(layer)

        # Handle mask if provided
        if mask is not None:
            self._send_layer_mask(layer, mask)

        # Set up derived layer processing if source_layer is set
        if resolved_source_layer is not None:
            self._setup_derived_layer(layer, resolved_source_layer)

        return layer

    def remove_layer(self, layer_id: str) -> None:
        """Remove a layer from the StreamView.

        :param layer_id: ID of the layer to remove
        """
        if layer_id in self._layers:
            layer = self._layers.pop(layer_id)

            # Clean up on_frame callback for derived layers
            if hasattr(layer, '_on_frame_callback') and hasattr(layer, '_source_stream'):
                try:
                    layer._source_stream.remove_on_frame(layer._on_frame_callback)
                except Exception:
                    pass

            layer.stop()
            self._update_layer_order()
            self.run_method("removeLayer", layer_id)

    def add_webrtc_layer(
        self,
        stream: VideoStream,
        *,
        z_index: int = 0,
        codec: str = "h264",
        bitrate: int = 5_000_000,
        target_fps: int | None = None,
        name: str = "",
    ) -> str:
        """Add a WebRTC-transported video layer.

        WebRTC provides efficient H.264/VP8 encoding, reducing bandwidth
        from ~40-50 Mbit (base64 JPEG) to ~2-5 Mbit.

        :param stream: VideoStream source for the layer
        :param z_index: Stacking order (higher = on top)
        :param codec: Video codec ('h264', 'vp8', 'vp9')
        :param bitrate: Target bitrate in bits per second
        :param target_fps: Target frame rate (None = use source fps)
        :param name: Display name for metrics
        :return: Layer ID
        :raises ImportError: If aiortc is not installed
        """
        if not AIORTC_AVAILABLE:
            raise ImportError(
                "aiortc is required for WebRTC layers. "
                "Install with: pip install aiortc"
            )

        # Initialize WebRTC manager on first use
        if self._webrtc_manager is None:
            self._webrtc_manager = WebRTCManager()

        # Generate layer ID
        layer_id = str(uuid.uuid4())

        # Store config
        config = WebRTCLayerConfig(
            stream=stream,
            z_index=z_index,
            codec=codec,
            bitrate=bitrate,
            target_fps=target_fps,
            width=self._width,
            height=self._height,
            name=name or f"WebRTC-{z_index}",
        )
        self._webrtc_layers[layer_id] = config

        # Queue the config for deferred start
        # The timer will start connections after a short delay to ensure JS is ready
        self._pending_webrtc_configs[layer_id] = config

        return layer_id

    def _start_webrtc_connection(self, layer_id: str, config: WebRTCLayerConfig) -> None:
        """Start a WebRTC connection for a layer."""
        # Capture dict reference - callback runs from another thread
        offers_dict = self._pending_webrtc_offers

        # The callback queues the offer for delivery by the main thread timer
        def on_offer(lid: str, offer: dict) -> None:
            # Queue the offer for delivery from the main thread
            # (run_method must be called from main event loop, not background thread)
            offers_dict[lid] = offer

        self._webrtc_manager.create_connection(layer_id, config, on_offer=on_offer)

    def _handle_component_ready(self, _e) -> None:
        """Handle component-ready event from JS."""
        self._component_ready = True
        self._start_pending_webrtc()

    def _start_pending_webrtc(self) -> None:
        """Start any pending WebRTC connections."""
        if not self._pending_webrtc_configs:
            return

        for layer_id, config in list(self._pending_webrtc_configs.items()):
            del self._pending_webrtc_configs[layer_id]
            self._start_webrtc_connection(layer_id, config)

    def _send_pending_webrtc_offers(self) -> None:
        """Process pending WebRTC configs and offers.

        Called by timer to:
        1. Start connections for pending configs (deferred from add_webrtc_layer)
        2. Send offers to JS once they're ready

        This ensures everything runs in the main thread context.
        """
        try:
            # First, start any pending configs
            if self._pending_webrtc_configs:
                for layer_id, config in list(self._pending_webrtc_configs.items()):
                    del self._pending_webrtc_configs[layer_id]
                    self._start_webrtc_connection(layer_id, config)

            # Then, send any pending offers
            if not self._pending_webrtc_offers:
                return

            # Process all pending offers
            offers_to_send = list(self._pending_webrtc_offers.items())
            self._pending_webrtc_offers.clear()

            for layer_id, offer in offers_to_send:
                cfg = self._webrtc_layers.get(layer_id)
                if cfg is None:
                    continue

                try:
                    self.run_method(
                        "setupWebRTCLayer",
                        layer_id,
                        offer,
                        cfg.z_index,
                        cfg.name,
                    )
                except Exception:
                    # Re-queue the offer for retry
                    self._pending_webrtc_offers[layer_id] = offer
        except Exception:
            pass  # Timer will retry on next tick

    def _handle_webrtc_answer(self, e) -> None:
        """Handle WebRTC answer from browser."""
        layer_id = e.args.get("layer_id")
        answer = e.args.get("answer")

        if layer_id and answer and self._webrtc_manager:
            self._webrtc_manager.handle_answer(layer_id, answer)

    def remove_webrtc_layer(self, layer_id: str) -> None:
        """Remove a WebRTC layer.

        :param layer_id: ID of the layer to remove
        """
        if layer_id in self._webrtc_layers:
            del self._webrtc_layers[layer_id]
            if self._webrtc_manager:
                self._webrtc_manager.close_connection(layer_id)
            self.run_method("removeWebRTCLayer", layer_id)

    def set_size(self, width: int, height: int) -> None:
        """Change the display size of the StreamView.

        Also updates all full-canvas layers to resize frames to the new size.

        :param width: New display width in pixels
        :param height: New display height in pixels
        """
        self._width = width
        self._height = height
        self._props["width"] = width
        self._props["height"] = height

        # Update target size for all full-canvas layers (no explicit width/height)
        for layer in self._layers.values():
            if layer.width is None and layer.height is None:
                layer.set_target_size(width, height)

        self.run_method("setSize", width, height)

    def set_fullscreen_mode(
        self,
        active: bool,
        screen_width: int = 0,
        screen_height: int = 0,
        video_width: int = 0,
        video_height: int = 0,
    ) -> None:
        """Update layer target sizes based on fullscreen mode and their fullscreen_scale setting.

        Call this when entering/exiting fullscreen to properly scale overlay layers.

        :param active: Whether fullscreen is active
        :param screen_width: Screen width in pixels (for fullscreen_scale="screen" layers)
        :param screen_height: Screen height in pixels
        :param video_width: Video/view width in pixels (for fullscreen_scale="video" layers)
        :param video_height: Video/view height in pixels
        """
        for layer in self._layers.values():
            # Only affect full-canvas layers (positioned layers keep their explicit size)
            if layer.width is not None or layer.height is not None:
                continue

            if active:
                if layer.fullscreen_scale == "screen" and screen_width > 0 and screen_height > 0:
                    # Render at screen resolution for sharper lines
                    layer.set_target_size(screen_width, screen_height)
                else:
                    # Match video resolution (default)
                    layer.set_target_size(video_width or self._width, video_height or self._height)
            else:
                # Exit fullscreen: use current view size
                layer.set_target_size(self._width, self._height)

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
        # Use provided name, or generate default from z_index
        display_name = layer.name or f"Layer {layer.z_index}"

        # Determine more specific source type for display
        source_type = layer.source_type
        if source_type == "stream" and layer.stream is not None:
            # Get the actual stream class name for more detail
            stream_class = type(layer.stream).__name__
            if stream_class == "VideoStream":
                source_type = "video"
            elif stream_class == "CustomStream":
                source_type = "custom"
            # else keep "stream"

        config = {
            "id": layer.id,
            "name": display_name,
            "z_index": layer.z_index,
            "target_fps": layer.target_fps,
            "is_static": layer.is_static,
            "source_type": source_type,
            "image_format": "PNG" if layer.use_png else "JPEG",
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

    def _send_layer_mask(self, layer: StreamViewLayer, mask: "Image | str") -> None:
        """Send a mask image to the client for a layer.

        :param layer: The layer to apply the mask to
        :param mask: Grayscale Image or data URL string
        """
        import base64

        # Convert Image to data URL if needed
        if isinstance(mask, str):
            # Already a URL or data URL
            mask_data = mask
        else:
            # Image object - encode as grayscale PNG
            from imagestag import Image

            if hasattr(mask, 'pixel_format') and mask.pixel_format.band_count > 1:
                # Convert to grayscale
                mask = mask.converted("GRAY")
            png_bytes = mask.to_png()
            if png_bytes:
                mask_data = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
            else:
                return

        # Send mask to client
        self.run_method("setLayerMask", layer.id, mask_data)

    def _setup_derived_layer(
        self, layer: StreamViewLayer, source_layer: StreamViewLayer
    ) -> None:
        """Set up frame processing for a derived layer.

        Subscribes to the source layer's stream (if present) and processes
        frames through the derived layer's pipeline.

        :param layer: The derived layer
        :param source_layer: The source layer to read frames from
        """
        import base64

        # Find the source stream to subscribe to
        source_stream = None
        if source_layer.stream is not None:
            source_stream = source_layer.stream
        elif source_layer.source_layer is not None:
            # Traverse up the chain to find a stream
            current = source_layer.source_layer
            while current is not None:
                if current.stream is not None:
                    source_stream = current.stream
                    break
                current = getattr(current, 'source_layer', None)

        if source_stream is None:
            # No stream in source chain - static source
            # For static sources, we'd need different handling
            logger.warning(
                f"Derived layer {layer.id} has no dynamic source stream - "
                "static source layers not yet supported for derived layers"
            )
            return

        # Check if the stream supports on_frame callbacks
        if not hasattr(source_stream, 'on_frame'):
            logger.warning(
                f"Source stream {type(source_stream).__name__} doesn't support "
                "on_frame callbacks - derived layer processing disabled"
            )
            return

        # Store reference for cleanup
        layer._source_stream = source_stream

        # Create the processing callback
        def process_frame(frame: "Image", timestamp: float) -> None:
            """Process a frame from the source and inject into derived layer."""
            try:
                from .timing import FrameMetadata, new_frame_metadata

                # Create metadata
                metadata = new_frame_metadata()
                metadata.capture_time = timestamp * 1000  # ms

                # Get the layer's position for cropping
                # If layer has explicit position, crop from source
                layer_x = layer.x or 0
                layer_y = layer.y or 0
                layer_w = layer.width or frame.width
                layer_h = layer.height or frame.height

                # Add overscan if specified
                overscan = layer.overscan
                crop_x = max(0, layer_x - overscan)
                crop_y = max(0, layer_y - overscan)
                crop_w = layer_w + 2 * overscan
                crop_h = layer_h + 2 * overscan

                # Crop region (ensure within bounds)
                x1 = crop_x
                y1 = crop_y
                x2 = min(crop_x + crop_w, frame.width)
                y2 = min(crop_y + crop_h, frame.height)

                if x2 <= x1 or y2 <= y1:
                    return  # Invalid crop region

                # Crop the frame
                cropped = frame.cropped((x1, y1, x2, y2))

                # Apply pipeline if present
                if layer.pipeline is not None:
                    for f in layer.pipeline.filters:
                        filter_start = FrameMetadata.now_ms()
                        cropped = f.apply(cropped)
                        filter_end = FrameMetadata.now_ms()
                        metadata.add_filter_timing(
                            f.__class__.__name__, filter_start, filter_end
                        )

                # Resize to target size if needed
                if layer._target_width > 0 and layer._target_height > 0:
                    if cropped.width != layer._target_width or cropped.height != layer._target_height:
                        cropped = cropped.resized((layer._target_width, layer._target_height))

                # Encode
                metadata.encode_start = FrameMetadata.now_ms()
                if layer.use_png:
                    img_bytes = cropped.to_png()
                    mime_type = "png"
                else:
                    img_bytes = cropped.to_jpeg(quality=layer.jpeg_quality)
                    mime_type = "jpeg"

                if img_bytes is None:
                    return

                metadata.frame_bytes = len(img_bytes)
                encoded = f"data:image/{mime_type};base64," + base64.b64encode(img_bytes).decode("ascii")
                metadata.encode_end = FrameMetadata.now_ms()
                metadata.send_time = FrameMetadata.now_ms()

                # Store frame dimensions
                metadata.frame_width = cropped.width
                metadata.frame_height = cropped.height

                # Inject into layer's buffer
                anchor_x = layer_x if overscan > 0 else None
                anchor_y = layer_y if overscan > 0 else None
                layer.inject_frame(
                    encoded,
                    timestamp,
                    anchor_x=anchor_x,
                    anchor_y=anchor_y,
                )

            except Exception as e:
                logger.debug(f"Derived layer frame processing error: {e}")

        # Register the callback
        source_stream.on_frame(process_frame)

        # Store callback reference for removal on cleanup
        layer._on_frame_callback = process_frame

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

    def _handle_size_changed(self, e: GenericEventArguments) -> None:
        """Handle size change event from JavaScript (e.g., fullscreen resize)."""
        args = e.args
        new_width = args.get("width", self._width)
        new_height = args.get("height", self._height)

        # Update internal dimensions (JS already resized the canvas)
        self._width = new_width
        self._height = new_height
        self._props["width"] = new_width
        self._props["height"] = new_height

        # Update target size for all full-canvas layers
        for layer in self._layers.values():
            if layer.width is None and layer.height is None:
                layer.set_target_size(new_width, new_height)

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
        # This handles cropping for WebSocket layers
        for layer in self._layers.values():
            layer.set_viewport(self._viewport)

            # If stream is paused, update from last frame to show zoomed view
            # All streams inherit from ImageStream which has is_paused property
            if layer.stream is not None and layer.stream.is_paused:
                layer.update_from_last_frame()

        # Also update WebRTC layer configs (they handle their own cropping)
        for config in self._webrtc_layers.values():
            config.set_viewport(self._viewport)

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
        # Start any pending WebRTC connections on first frame request
        # (this is a reliable trigger since frame requests definitely work)
        if self._pending_webrtc_configs:
            self._start_pending_webrtc()

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
            _timestamp, encoded, metadata = frame_data
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

        # Get frame from stream - returns (frame, frame_index) tuple
        timestamp = time.perf_counter()
        try:
            frame_result = layer.stream.get_frame(timestamp)
        except Exception:
            return None

        # Unpack tuple from get_frame()
        if isinstance(frame_result, tuple):
            frame, _ = frame_result
        else:
            frame = frame_result

        if frame is None:
            return None

        # Handle multi-output streams
        if isinstance(frame, dict):
            if layer.stream_output is None:
                frame = next(iter(frame.values()))
            else:
                frame = frame.get(layer.stream_output)
                if frame is None:
                    return None

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

        # Safety limit - if too many pending requests, clear all to prevent memory leak
        if len(self._pending_requests) > 100:
            import sys
            print("Warning: Too many pending frame requests, clearing", file=sys.stderr)
            self._pending_requests.clear()

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
        self._webrtc_timer.deactivate()  # Also clean up WebRTC offer timer
        super()._handle_delete()
