"""Layer and stream classes for StreamView component.

This module defines the core abstractions for video/image streaming:
- ImageStream: Base class for all frame sources
- VideoStream: OpenCV-based video file playback (seekable)
- CameraStream: Live camera/webcam capture
- GeneratorStream: User-provided rendering callback (replaces CustomStream)
- StreamViewLayer: A layer in the StreamView compositing stack

The stream classes are now defined in imagestag.streams and re-exported here
for backwards compatibility.
"""

from __future__ import annotations

import base64
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imagestag import Image
    from imagestag.filters import FilterPipeline

from .timing import FrameMetadata, new_frame_metadata

# Import stream classes from the new streams package
from imagestag.streams import (
    ImageStream,
    VideoStream,
    CameraStream,
    GeneratorStream,
    FrameResult,
)

# Backwards compatibility alias
CustomStream = GeneratorStream


@dataclass
class StreamViewLayer:
    """A layer in the StreamView compositing stack.

    Each layer has one source (stream, URL, static Image, or source_layer)
    and can have its own target FPS and optional filter pipeline.

    For multi-output streams, multiple layers can share the same stream
    with different stream_output keys.

    Layers can also derive content from other layers using source_layer,
    which enables layered composition (e.g., applying filters to a crop
    of another layer's content).

    Attributes:
        id: Unique layer identifier
        name: User-friendly display name for metrics overlay
        z_index: Stacking order (higher = on top)
        target_fps: Desired update rate for this layer
        pipeline: Optional FilterPipeline to apply to frames
        stream: Dynamic ImageStream source
        stream_output: Output key for multi-output streams
        url: Static URL or data URL
        image: Static Image object
        source_layer: Another layer to read frames from
        buffer_size: Number of frames to buffer ahead
        jpeg_quality: JPEG encoding quality (1-100)
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""  # User-friendly display name (defaults to "Layer {z_index}" if empty)
    z_index: int = 0
    target_fps: int = 60
    pipeline: "FilterPipeline | None" = None

    # Source - exactly ONE should be set (or use source_layer for derived layers)
    stream: ImageStream | None = None
    stream_output: str | None = None  # For multi-output streams
    url: str | None = None
    image: "Image | None" = None
    source_layer: "StreamViewLayer | None" = None  # Read frames from another layer

    # Buffering configuration
    buffer_size: int = 4
    jpeg_quality: int = 85
    use_png: bool = False  # Use PNG for transparent layers (slower but supports alpha)

    # Position/size (None = fill canvas, otherwise specify in pixels)
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None

    # Piggyback mode - frames injected directly, no producer thread
    # When True, this layer's frames are injected by another source (e.g., via on_frame callback)
    # This eliminates producer thread scheduling delay for dependent layers
    piggyback: bool = False

    # Depth - controls how layer responds to viewport zoom/pan
    # 0.0 = FIXED    - Screen-locked (HUD, overlays, crosshairs)
    # 1.0 = CONTENT  - Follows viewport exactly (main video/image) - DEFAULT
    # 0.5 = DISTANT  - Parallax background (moves at 50% speed)
    # 2.0 = CLOSE    - Parallax foreground (moves at 200% speed)
    depth: float = 1.0

    # Overscan - extra pixels around displayed area (for positioned layers)
    # When set, the layer crops/renders extra pixels beyond the display size.
    # This prevents showing stale content when the layer moves, since the
    # "old" content includes a border that can fill the gap during movement.
    # Set to 0 to disable (default).
    overscan: int = 0

    # Fullscreen scaling mode - controls how layer resolution behaves in fullscreen
    # "video" = Match video resolution (e.g., 1920x1080 overlay on 1920x1080 video)
    # "screen" = Render at screen resolution for sharper lines (best for PNG overlays)
    fullscreen_scale: str = "video"

    # Runtime state (not serialized)
    _frame_buffer: deque = field(default_factory=deque, repr=False)
    _producer_thread: threading.Thread | None = field(default=None, repr=False)
    _running: bool = field(default=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _last_frame_time: float = field(default=0.0, repr=False)
    # Viewport for server-side cropping (normalized 0-1 coords)
    _viewport_x: float = field(default=0.0, repr=False)
    _viewport_y: float = field(default=0.0, repr=False)
    _viewport_w: float = field(default=1.0, repr=False)
    _viewport_h: float = field(default=1.0, repr=False)
    _viewport_zoom: float = field(default=1.0, repr=False)
    # Target display size (for resizing frames before transfer)
    _target_width: int = field(default=0, repr=False)
    _target_height: int = field(default=0, repr=False)
    # Anchor position for overscan layers (where the content was centered when captured)
    _anchor_x: int = field(default=0, repr=False)
    _anchor_y: int = field(default=0, repr=False)

    # Metrics
    actual_fps: float = field(default=0.0, repr=False)
    frames_produced: int = field(default=0, repr=False)
    frames_dropped: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        """Validate that exactly one source is set (unless piggyback mode)."""
        # Initialize frame buffer with maxlen to auto-enforce bounds
        self._frame_buffer = deque(maxlen=self.buffer_size)

        sources = [self.stream, self.url, self.image, self.source_layer]
        active_sources = sum(1 for s in sources if s is not None)

        # Piggyback layers receive frames via inject_frame(), no source needed
        if self.piggyback:
            if active_sources > 1:
                raise ValueError("Piggyback layer can have at most one source type")
            return

        # Derived layers (with source_layer) are always piggyback
        if self.source_layer is not None:
            self.piggyback = True  # Auto-enable piggyback for derived layers
            return

        if active_sources == 0:
            raise ValueError("StreamViewLayer requires a source (stream, url, image, or source_layer)")
        if active_sources > 1:
            raise ValueError("StreamViewLayer can only have one source type")

    @property
    def is_static(self) -> bool:
        """Whether this layer has a static (non-streaming) source."""
        return self.url is not None or self.image is not None

    @property
    def source_type(self) -> str:
        """Return the type of source ('stream', 'url', 'image', or 'derived')."""
        if self.source_layer is not None:
            return "derived"
        elif self.stream is not None:
            return "stream"
        elif self.url is not None:
            return "url"
        else:
            return "image"

    def start(self) -> None:
        """Start the layer's frame production."""
        if self._running:
            return

        self._running = True
        self._frame_buffer.clear()

        # Start the stream if present
        if self.stream is not None:
            self.stream.start()

            # In piggyback mode, frames are injected externally - no producer thread needed
            if self.piggyback:
                return

            # Start producer thread for buffering
            self._producer_thread = threading.Thread(
                target=self._producer_loop,
                daemon=True,
                name=f"StreamViewLayer-{self.id}",
            )
            self._producer_thread.start()

    def stop(self) -> None:
        """Stop the layer's frame production.

        Note: Does NOT stop the underlying stream, as it may be shared
        with other layers (e.g., WebRTC, lenses). The stream owner is
        responsible for stopping it when appropriate.
        """
        self._running = False

        if self._producer_thread is not None:
            self._producer_thread.join(timeout=1.0)
            self._producer_thread = None

    def _get_effective_fps(self) -> float:
        """Get effective FPS accounting for playback speed.

        Uses stream's source fps (not target_fps) scaled by playback speed.
        At 1x with 24fps source: 24fps output
        At 2x with 24fps source: 48fps output
        At 4x with 24fps source: 60fps output (capped by max_fps)
        """
        # Use stream's source fps if available
        if self.stream is not None and hasattr(self.stream, 'fps'):
            base_fps = self.stream.fps
            speed = getattr(self.stream, 'playback_speed', 1.0)
            fps = base_fps * speed
            # Cap by stream's max_fps if set
            max_fps = getattr(self.stream, 'max_fps', None)
            if max_fps is not None:
                fps = min(fps, max_fps)
            return max(1.0, fps)
        # Fall back to target_fps for non-video streams
        return float(self.target_fps)

    def _producer_loop(self) -> None:
        """Background thread that produces frames ahead of time."""
        next_frame_time = time.perf_counter()
        start_time = next_frame_time
        last_frame_index = -1

        while self._running:
            # Check if buffer is full
            with self._lock:
                if len(self._frame_buffer) >= self.buffer_size:
                    # Buffer full, wait a bit
                    time.sleep(0.001)
                    continue

            # Get timestamp for this frame
            current_time = time.perf_counter()
            timestamp = current_time - start_time

            # Get frame from stream - new API returns (frame, frame_index)
            try:
                frame_result = self.stream.get_frame(timestamp)
            except Exception:
                frame_result = (None, last_frame_index)

            # Handle the new tuple[Image | None, int] return type
            if isinstance(frame_result, tuple) and len(frame_result) == 2:
                frame, frame_index = frame_result
            else:
                # Fallback for any unexpected return type
                frame = frame_result if not isinstance(frame_result, tuple) else None
                frame_index = last_frame_index

            # Skip if no new frame (same index as last time)
            if frame is None or frame_index == last_frame_index:
                time.sleep(0.001)
                continue

            last_frame_index = frame_index

            # Create metadata for timing tracking
            metadata = new_frame_metadata()

            # Get capture timestamp from stream (ImageStream base class guarantees this)
            metadata.capture_time = self.stream.last_frame_timestamp * 1000

            # Apply filter pipeline if present
            if self.pipeline is not None:
                try:
                    # Track timing for each filter
                    for f in self.pipeline.filters:
                        filter_start = FrameMetadata.now_ms()
                        frame = f.apply(frame)
                        filter_end = FrameMetadata.now_ms()
                        metadata.add_filter_timing(
                            f.__class__.__name__,
                            filter_start,
                            filter_end
                        )
                except Exception as e:
                    import sys
                    print(f"Filter pipeline error: {e}", file=sys.stderr)
                    pass  # Use unfiltered frame

            # Apply viewport cropping based on effective viewport (respects depth)
            # depth=0.0 layers are fixed and never cropped
            # depth=1.0 layers follow viewport exactly
            # For nav window: generate a small thumbnail of full frame before cropping
            eff_zoom = self.effective_zoom
            if eff_zoom > 1.0 and frame is not None:
                try:
                    # Generate nav thumbnail BEFORE cropping (small, for nav window)
                    # Scale to ~160x90 maintaining aspect ratio
                    thumb_height = 90
                    thumb_width = int(frame.width * thumb_height / frame.height)
                    thumb = frame.resized((thumb_width, thumb_height))
                    thumb_bytes = thumb.to_jpeg(quality=60)
                    if thumb_bytes:
                        metadata.nav_thumbnail = base64.b64encode(thumb_bytes).decode("ascii")

                    # Now crop the frame
                    source_width, source_height = frame.width, frame.height
                    x1, y1, x2, y2 = self.get_effective_crop(source_width, source_height)
                    x1 = max(0, min(x1, source_width - 1))
                    y1 = max(0, min(y1, source_height - 1))
                    x2 = max(x1 + 1, min(x2, source_width))
                    y2 = max(y1 + 1, min(y2, source_height))
                    frame = frame.cropped((x1, y1, x2, y2))
                except Exception:
                    pass  # Use uncropped frame on error

            # Resize frame to target display size (reduces bandwidth)
            if frame is not None and self._target_width > 0 and self._target_height > 0:
                # Only resize if frame is larger than target
                if frame.width > self._target_width or frame.height > self._target_height:
                    try:
                        frame = frame.resized((self._target_width, self._target_height))
                    except Exception:
                        pass  # Use original frame on error

            # Track frame dimensions for resolution display
            if frame is not None:
                metadata.frame_width = frame.width
                metadata.frame_height = frame.height

            # Encode frame
            metadata.encode_start = FrameMetadata.now_ms()
            try:
                if self.use_png:
                    img_bytes = frame.to_png()
                    mime_type = "png"
                else:
                    img_bytes = frame.to_jpeg(quality=self.jpeg_quality)
                    mime_type = "jpeg"
                if img_bytes is None:
                    continue
                metadata.frame_bytes = len(img_bytes)
                encoded = f"data:image/{mime_type};base64," + base64.b64encode(img_bytes).decode("ascii")
            except Exception:
                continue
            metadata.encode_end = FrameMetadata.now_ms()
            metadata.send_time = FrameMetadata.now_ms()

            # Calculate effective FPS for this frame (dynamic based on playback speed)
            effective_fps = self._get_effective_fps()
            frame_interval = 1.0 / effective_fps

            # Add to buffer with metadata (include buffer occupancy and effective FPS)
            with self._lock:
                metadata.buffer_length = len(self._frame_buffer) + 1  # +1 for this frame
                metadata.buffer_capacity = self.buffer_size
                metadata.effective_fps = effective_fps  # For JS to update request timing
                self._frame_buffer.append((timestamp, encoded, metadata))
                self.frames_produced += 1
            next_frame_time += frame_interval
            sleep_time = next_frame_time - time.perf_counter()
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif sleep_time < -frame_interval:
                # Falling behind, reset timing
                next_frame_time = time.perf_counter()
                self.frames_dropped += 1

    def get_buffered_frame(self) -> tuple[float, str, FrameMetadata] | None:
        """Get the next buffered frame.

        :return: Tuple of (timestamp, base64_data, metadata) or None if buffer empty
        """
        with self._lock:
            if self._frame_buffer:
                return self._frame_buffer.popleft()
            return None

    def get_static_frame(self) -> str | None:
        """Get the static frame (for url/image sources).

        :return: URL string or base64 data URL
        """
        if self.url is not None:
            return self.url

        if self.image is not None:
            # Encode to data URL (PNG for alpha, JPEG otherwise)
            fmt = "png" if self.use_png else "jpeg"
            return self.image.to_data_url(format=fmt, quality=self.jpeg_quality)

        return None

    def inject_frame(
        self,
        encoded: str,
        birth_time: float,
        step_timings: dict[str, float] | None = None,
        anchor_x: int | None = None,
        anchor_y: int | None = None,
    ) -> None:
        """Inject a pre-encoded frame directly into the buffer.

        Use this in piggyback mode to synchronously inject frames from
        another source's on_frame callback. This eliminates producer thread
        scheduling delay - the frame is available immediately.

        :param encoded: Pre-encoded base64 data URL (data:image/jpeg;base64,...)
        :param birth_time: Original capture time (perf_counter seconds)
        :param step_timings: Optional dict of step durations in ms (e.g., {'crop_ms': 0.1})
        :param anchor_x: X position this frame's content is centered on (for overscan layers)
        :param anchor_y: Y position this frame's content is centered on (for overscan layers)
        """
        # Build metadata
        metadata = new_frame_metadata()
        metadata.capture_time = birth_time * 1000  # Convert to ms

        # Add step timings if provided
        if step_timings:
            for step_name, duration_ms in step_timings.items():
                display_name = step_name.replace('_ms', '').capitalize()
                metadata.add_filter_timing(display_name, 0, duration_ms)

        # No encoding time - already pre-encoded
        metadata.encode_start = FrameMetadata.now_ms()
        metadata.encode_end = metadata.encode_start
        metadata.send_time = FrameMetadata.now_ms()

        # Estimate frame size from base64 data (base64 is ~4/3 of binary)
        metadata.frame_bytes = len(encoded) * 3 // 4

        # Add anchor position for overscan layers
        if anchor_x is not None and anchor_y is not None:
            metadata.anchor_x = anchor_x
            metadata.anchor_y = anchor_y
            # Also store in layer for reference
            self._anchor_x = anchor_x
            self._anchor_y = anchor_y

        # Inject directly into buffer (include buffer occupancy)
        timestamp = time.perf_counter()
        with self._lock:
            # Enforce buffer limit - drop oldest frames if at capacity
            while len(self._frame_buffer) >= self.buffer_size:
                self._frame_buffer.popleft()
            metadata.buffer_length = len(self._frame_buffer) + 1  # +1 for this frame
            metadata.buffer_capacity = self.buffer_size
            self._frame_buffer.append((timestamp, encoded, metadata))
            self.frames_produced += 1

    def set_viewport(self, viewport) -> None:
        """Set the viewport for server-side cropping.

        :param viewport: Viewport object with x, y, width, height, zoom
        """
        with self._lock:
            self._viewport_x = viewport.x
            self._viewport_y = viewport.y
            self._viewport_w = viewport.width
            self._viewport_h = viewport.height
            self._viewport_zoom = viewport.zoom

    def set_target_size(self, width: int, height: int) -> None:
        """Set the target display size for frame resizing.

        Frames will be resized to this size before encoding to reduce bandwidth.
        For positioned layers, use the layer's width/height.
        For full-canvas layers, use the view's dimensions.

        :param width: Target width in pixels
        :param height: Target height in pixels
        """
        with self._lock:
            self._target_width = width
            self._target_height = height

    def get_viewport_crop(self, source_width: int, source_height: int) -> tuple[int, int, int, int]:
        """Get crop rectangle for current viewport in source image pixels.

        :param source_width: Width of source image in pixels
        :param source_height: Height of source image in pixels
        :return: Tuple of (x1, y1, x2, y2) crop coordinates
        """
        with self._lock:
            x1 = int(self._viewport_x * source_width)
            y1 = int(self._viewport_y * source_height)
            x2 = int((self._viewport_x + self._viewport_w) * source_width)
            y2 = int((self._viewport_y + self._viewport_h) * source_height)
            return (x1, y1, x2, y2)

    @property
    def is_zoomed(self) -> bool:
        """Whether the viewport is zoomed (zoom > 1)."""
        return self._viewport_zoom > 1.0

    def get_effective_viewport(self) -> tuple[float, float, float, float, float]:
        """Calculate effective viewport based on layer depth.

        Depth controls how much the layer follows viewport changes:
        - depth=0.0: Fixed layer, always shows full content
        - depth=1.0: Content layer, follows viewport exactly
        - depth<1.0: Parallax background, moves slower
        - depth>1.0: Parallax foreground, moves faster

        :return: Tuple of (x, y, width, height, zoom) for effective viewport
        """
        with self._lock:
            if self.depth == 0.0:
                # Fixed layer - always show full content
                return (0.0, 0.0, 1.0, 1.0, 1.0)

            if self.depth == 1.0:
                # Content layer - use viewport directly
                return (
                    self._viewport_x,
                    self._viewport_y,
                    self._viewport_w,
                    self._viewport_h,
                    self._viewport_zoom,
                )

            # Parallax: interpolate between fixed (0) and content (1)
            # Center of viewport in normalized coords
            cx = self._viewport_x + self._viewport_w / 2
            cy = self._viewport_y + self._viewport_h / 2

            # Apply depth factor to offset from center (0.5, 0.5)
            eff_cx = 0.5 + (cx - 0.5) * self.depth
            eff_cy = 0.5 + (cy - 0.5) * self.depth

            # Apply depth factor to zoom
            eff_zoom = 1 + (self._viewport_zoom - 1) * self.depth
            eff_w = 1 / eff_zoom if eff_zoom > 0 else 1.0
            eff_h = 1 / eff_zoom if eff_zoom > 0 else 1.0

            return (
                max(0.0, min(1.0 - eff_w, eff_cx - eff_w / 2)),
                max(0.0, min(1.0 - eff_h, eff_cy - eff_h / 2)),
                eff_w,
                eff_h,
                eff_zoom,
            )

    def get_effective_crop(self, source_width: int, source_height: int) -> tuple[int, int, int, int]:
        """Get crop rectangle based on effective viewport for this layer's depth.

        :param source_width: Width of source image in pixels
        :param source_height: Height of source image in pixels
        :return: Tuple of (x1, y1, x2, y2) crop coordinates
        """
        eff_x, eff_y, eff_w, eff_h, _ = self.get_effective_viewport()
        x1 = int(eff_x * source_width)
        y1 = int(eff_y * source_height)
        x2 = int((eff_x + eff_w) * source_width)
        y2 = int((eff_y + eff_h) * source_height)
        return (x1, y1, x2, y2)

    @property
    def effective_zoom(self) -> float:
        """Get the effective zoom level for this layer based on depth."""
        _, _, _, _, zoom = self.get_effective_viewport()
        return zoom

    def update_from_last_frame(self) -> bool:
        """Update the layer using the last frame from the stream.

        Useful for updating the view when video is paused but the
        viewport has changed (e.g., zoom/pan).

        :return: True if frame was produced, False otherwise
        """
        import base64

        if self.stream is None:
            return False

        # Get last frame from stream (ImageStream base class guarantees this property)
        frame = self.stream.last_frame
        if frame is None:
            return False

        # Create metadata for timing tracking
        metadata = new_frame_metadata()

        # Get capture timestamp from stream (ImageStream base class guarantees this)
        metadata.capture_time = self.stream.last_frame_timestamp * 1000

        # Apply filter pipeline if present
        if self.pipeline is not None:
            try:
                for f in self.pipeline.filters:
                    filter_start = FrameMetadata.now_ms()
                    frame = f.apply(frame)
                    filter_end = FrameMetadata.now_ms()
                    metadata.add_filter_timing(
                        f.__class__.__name__,
                        filter_start,
                        filter_end
                    )
            except Exception:
                pass  # Use unfiltered frame

        # Apply viewport cropping based on effective viewport (respects depth)
        eff_zoom = self.effective_zoom
        if eff_zoom > 1.0 and frame is not None:
            try:
                x1, y1, x2, y2 = self.get_effective_crop(frame.width, frame.height)
                x1 = max(0, min(x1, frame.width - 1))
                y1 = max(0, min(y1, frame.height - 1))
                x2 = max(x1 + 1, min(x2, frame.width))
                y2 = max(y1 + 1, min(y2, frame.height))

                if x2 > x1 and y2 > y1:
                    frame = frame.cropped((x1, y1, x2, y2))
            except Exception:
                pass  # Use uncropped frame

        # Resize to target dimensions
        if self._target_width > 0 and self._target_height > 0 and frame is not None:
            if frame.width != self._target_width or frame.height != self._target_height:
                frame = frame.resized((self._target_width, self._target_height))

        # Encode
        metadata.encode_start = FrameMetadata.now_ms()
        try:
            if self.use_png:
                img_bytes = frame.to_png()
                mime_type = "png"
            else:
                img_bytes = frame.to_jpeg(quality=self.jpeg_quality)
                mime_type = "jpeg"

            if img_bytes is None:
                return False

            metadata.frame_bytes = len(img_bytes)
            encoded = f"data:image/{mime_type};base64," + base64.b64encode(img_bytes).decode("ascii")
            metadata.encode_end = FrameMetadata.now_ms()
            metadata.send_time = FrameMetadata.now_ms()

            # Inject into buffer
            timestamp = time.perf_counter()
            with self._lock:
                self._frame_buffer.clear()  # Clear old frames
                self._frame_buffer.append((timestamp, encoded, metadata))
                self.frames_produced += 1

            return True
        except Exception:
            return False
