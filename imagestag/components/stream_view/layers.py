"""Layer and stream classes for StreamView component.

This module defines the core abstractions for video/image streaming:
- ImageStream: Base class for all frame sources
- VideoStream: OpenCV-based video file and camera capture
- CustomStream: User-provided rendering callback
- StreamViewLayer: A layer in the StreamView compositing stack
"""

from __future__ import annotations

import base64
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Literal

if TYPE_CHECKING:
    from imagestag import Image
    from imagestag.filters import FilterPipeline

from .timing import FrameMetadata, new_frame_metadata


# Type alias for frame callback return types
# Can return:
#   - Image: single frame
#   - dict[str, Image]: multi-output streams
#   - tuple[Image, float]: frame with birth timestamp (for frame sharing)
#   - tuple[Image, float, dict]: frame with birth timestamp and step timings
#   - tuple[Image, float, dict, str]: frame with birth timestamp, step timings, and pre-encoded data
#   - None: no frame available
FrameResult = "Image | dict[str, Image] | tuple | None"


class ImageStream(ABC):
    """Base class for all frame sources.

    Subclasses must implement get_frame() to provide frames on demand.
    The stream can operate in different execution modes:
    - 'sync': get_frame runs in the main thread
    - 'async': get_frame is awaited
    - 'thread': get_frame runs in a background thread (default)
    """

    def __init__(self) -> None:
        self._running = False
        self._mode: Literal["sync", "async", "thread"] = "thread"

    @abstractmethod
    def get_frame(self, timestamp: float) -> FrameResult:
        """Get a frame at the given timestamp.

        :param timestamp: Current playback time in seconds
        :return: Single Image, dict of named Images (multi-output), or None to skip
        """
        ...

    @property
    def mode(self) -> Literal["sync", "async", "thread"]:
        """Execution mode for get_frame calls."""
        return self._mode

    def start(self) -> None:
        """Start the stream (called when StreamView starts)."""
        self._running = True

    def stop(self) -> None:
        """Stop the stream (called when StreamView stops)."""
        self._running = False

    @property
    def is_running(self) -> bool:
        """Whether the stream is currently running."""
        return self._running


class VideoStream(ImageStream):
    """OpenCV-based video file or camera capture.

    Supports looping for video files and automatic frame rate detection.
    Uses timestamp-based frame seeking to maintain correct playback speed.

    The `last_frame` property provides thread-safe access to the most recently
    captured frame, enabling frame sharing with other streams (e.g., thermal lens).

    Example:
        # Video file
        stream = VideoStream('/path/to/video.mp4', loop=True)

        # Webcam (device 0)
        stream = VideoStream(0)

        # Frame sharing - another stream can access the latest frame
        thermal_frame = stream.last_frame  # Get the same frame video is showing
    """

    def __init__(
        self,
        path: str | int,
        *,
        loop: bool = True,
        target_fps: float | None = None,
    ) -> None:
        """Initialize video stream.

        :param path: File path for video, or device index for camera (0, 1, etc.)
        :param loop: Whether to loop video files (ignored for cameras)
        :param target_fps: Target frame rate (None = use source fps)
        """
        super().__init__()
        self._path = path
        self._loop = loop
        self._target_fps = target_fps
        self._cap = None
        self._source_fps: float = 30.0
        self._frame_count: int = 0
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._pause_time: float = 0.0  # Time when paused
        self._paused_elapsed: float = 0.0  # Accumulated elapsed time when paused
        self._last_frame_index: int = -1
        self._is_camera: bool = isinstance(path, int)
        # Frame sharing - stores the most recent frame WITH its capture timestamp
        # This allows dependent streams to know the true "birth" time of the frame
        self._last_frame: "Image | None" = None
        self._last_frame_timestamp: float = 0.0  # perf_counter timestamp when frame was captured
        self._last_frame_lock = threading.Lock()
        # Event-based notification for dependent streams
        self._frame_event = threading.Event()
        self._frame_subscribers: list[threading.Event] = []
        # Synchronous callbacks - run IMMEDIATELY when frame is captured (before encoding)
        self._on_frame_callbacks: list[Callable[["Image", float], None]] = []

    def start(self) -> None:
        """Open the video capture."""
        # If already running (e.g., after resume), don't reset
        if self._running and self._cap is not None and self._cap.isOpened():
            return

        cv2 = _get_cv2()
        if cv2 is None:
            raise RuntimeError("OpenCV (cv2) is required for VideoStream")

        # Only open capture if not already open
        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self._path)
            if not self._cap.isOpened():
                raise RuntimeError(f"Failed to open video source: {self._path}")

            # Get source properties
            self._source_fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
            self._frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self._start_time = time.perf_counter()
            self._last_frame_index = -1

        super().start()

    def stop(self) -> None:
        """Release the video capture."""
        super().stop()
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None

    def pause(self) -> None:
        """Pause video playback (preserves position for resume)."""
        if self._running and self._pause_time == 0.0:
            self._pause_time = time.perf_counter()
            self._running = False

    def resume(self) -> None:
        """Resume video playback from paused position."""
        if not self._running and self._pause_time > 0.0:
            # Calculate how long we were paused
            pause_duration = time.perf_counter() - self._pause_time
            # Offset start time to account for pause
            self._start_time += pause_duration
            self._pause_time = 0.0
            self._running = True

    def get_frame(self, timestamp: float) -> FrameResult:
        """Read the frame corresponding to the current playback time.

        For video files, seeks to the correct frame based on elapsed time.
        For cameras, just reads the next available frame.

        :param timestamp: Timestamp from caller (not used, we track our own time)
        :return: Image frame or None if no frame available
        """
        from imagestag import Image

        # Return None when paused (but don't close capture)
        if not self._running:
            return None

        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                return None

            cv2 = _get_cv2()

            # For cameras, just read next frame
            if self._is_camera:
                # Record EXACT moment of capture
                capture_time = time.perf_counter()
                ret, frame = self._cap.read()
                if not ret:
                    return None
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = Image(frame_rgb, pixel_format="RGB")
                # Run synchronous callbacks FIRST (before storing/notifying)
                self._run_on_frame_callbacks(result, capture_time)
                # Store for frame sharing
                with self._last_frame_lock:
                    self._last_frame = result
                    self._last_frame_timestamp = capture_time
                # Notify async subscribers
                self._notify_subscribers()
                return result

            # For video files, calculate which frame we should be showing
            elapsed = time.perf_counter() - self._start_time
            target_frame = int(elapsed * self._source_fps)

            # Handle looping
            if self._frame_count > 0:
                if target_frame >= self._frame_count:
                    if self._loop:
                        # Loop: reset start time and frame
                        loops = target_frame // self._frame_count
                        self._start_time += loops * (self._frame_count / self._source_fps)
                        target_frame = target_frame % self._frame_count
                    else:
                        return None  # Video ended

            # Only read if we need a new frame
            if target_frame == self._last_frame_index:
                return None  # Same frame, skip

            # Seek if we're not at the right position
            current_pos = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
            if current_pos != target_frame:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            # Record EXACT moment of capture (before cv2.read())
            capture_time = time.perf_counter()
            ret, frame = self._cap.read()

            if not ret:
                if self._loop and self._frame_count > 0:
                    # Loop back to start
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self._start_time = time.perf_counter()
                    self._last_frame_index = -1
                    capture_time = time.perf_counter()
                    ret, frame = self._cap.read()
                    if not ret:
                        return None
                    target_frame = 0
                else:
                    return None

            # Track which frame we just read
            self._last_frame_index = target_frame

            # Convert BGR (OpenCV default) to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = Image(frame_rgb, pixel_format="RGB")

            # Run synchronous callbacks FIRST (before storing/notifying)
            # This allows dependent streams to process the frame immediately
            self._run_on_frame_callbacks(result, capture_time)

            # Store for frame sharing (with capture timestamp)
            with self._last_frame_lock:
                self._last_frame = result
                self._last_frame_timestamp = capture_time

            # Notify async subscribers that a new frame is available
            self._notify_subscribers()

            return result

    @property
    def fps(self) -> float:
        """Source frame rate."""
        return self._target_fps or self._source_fps

    @property
    def frame_count(self) -> int:
        """Total number of frames (0 for cameras/live streams)."""
        return self._frame_count

    @property
    def last_frame(self) -> "Image | None":
        """Get the most recently captured frame (thread-safe).

        Use this for frame sharing - e.g., a thermal lens can process
        the same frame the main video is displaying.
        """
        with self._last_frame_lock:
            return self._last_frame

    @property
    def last_frame_timestamp(self) -> float:
        """Get the capture timestamp of the last frame (perf_counter seconds).

        This is the exact moment the frame was read from the video source.
        Use this to calculate true birth-to-display latency.
        """
        with self._last_frame_lock:
            return self._last_frame_timestamp

    def get_last_frame_with_timestamp(self) -> tuple["Image | None", float]:
        """Get the last frame and its capture timestamp atomically.

        :return: Tuple of (frame, capture_timestamp_seconds)
        """
        with self._last_frame_lock:
            return self._last_frame, self._last_frame_timestamp

    def subscribe(self) -> threading.Event:
        """Subscribe to frame events. Returns an Event that is set when new frame arrives.

        Dependent streams should wait on this event instead of polling.
        """
        event = threading.Event()
        self._frame_subscribers.append(event)
        return event

    def unsubscribe(self, event: threading.Event) -> None:
        """Unsubscribe from frame events."""
        if event in self._frame_subscribers:
            self._frame_subscribers.remove(event)

    def _notify_subscribers(self) -> None:
        """Notify all subscribers that a new frame is available."""
        for event in self._frame_subscribers:
            event.set()

    def wait_for_frame(self, timeout: float = 0.1) -> bool:
        """Wait for a new frame to be captured.

        :param timeout: Max time to wait in seconds
        :return: True if frame arrived, False if timeout
        """
        self._frame_event.clear()
        return self._frame_event.wait(timeout)

    def on_frame(self, callback: Callable[["Image", float], None]) -> None:
        """Register a callback to run synchronously when a frame is captured.

        The callback runs in the video producer thread, IMMEDIATELY after capture
        and BEFORE encoding. This is the fastest way to process dependent data.

        :param callback: Function(frame, capture_timestamp) to call
        """
        self._on_frame_callbacks.append(callback)

    def remove_on_frame(self, callback: Callable[["Image", float], None]) -> None:
        """Remove an on_frame callback."""
        if callback in self._on_frame_callbacks:
            self._on_frame_callbacks.remove(callback)

    def _run_on_frame_callbacks(self, frame: "Image", timestamp: float) -> None:
        """Run all registered on_frame callbacks."""
        for callback in self._on_frame_callbacks:
            try:
                callback(frame, timestamp)
            except Exception:
                pass  # Don't let callback errors break video capture


class CustomStream(ImageStream):
    """User-provided render handler for custom frame generation.

    The handler receives a timestamp and returns either:
    - A single Image (for single-output streams)
    - A dict of {output_name: Image} (for multi-output streams)
    - None to skip the frame

    Example:
        # Single output
        def render_frame(t: float) -> Image:
            return generate_procedural_image(t)

        stream = CustomStream(render_frame)

        # Multi-output (e.g., face detector with multiple overlays)
        def detect_and_draw(t: float) -> dict[str, Image]:
            return {
                'boxes': draw_detection_boxes(...),
                'heatmap': generate_heatmap(...),
            }

        stream = CustomStream(detect_and_draw, mode='thread')

        # Dependent stream - triggered by source, not its own timing
        stream = CustomStream(handler, source=video_stream)
    """

    def __init__(
        self,
        handler: Callable[[float], FrameResult],
        mode: Literal["sync", "async", "thread"] = "thread",
        source: "VideoStream | None" = None,
    ) -> None:
        """Initialize custom stream.

        :param handler: Callable that takes timestamp and returns Image(s)
        :param mode: Execution mode ('sync', 'async', 'thread')
        :param source: Optional source stream to depend on (for frame-synced processing)
        """
        super().__init__()
        self._handler = handler
        self._mode = mode
        self._source = source
        self._last_result: FrameResult = None
        self._last_source_timestamp: float = 0.0
        self._processing_lock = threading.Lock()

    def get_frame(self, timestamp: float) -> FrameResult:
        """Call the user handler to get a frame.

        If source is set, only processes when source has a new frame.

        :param timestamp: Current playback time in seconds
        :return: Result from the handler
        """
        if self._source is not None:
            # Check if source has a new frame
            source_ts = self._source.last_frame_timestamp
            if source_ts == self._last_source_timestamp and self._last_result is not None:
                # Return cached result - source hasn't updated
                return self._last_result

            # Process new frame
            with self._processing_lock:
                self._last_source_timestamp = source_ts
                self._last_result = self._handler(timestamp)
                return self._last_result

        return self._handler(timestamp)

    @property
    def source(self) -> "VideoStream | None":
        """The source stream this depends on."""
        return self._source


@dataclass
class StreamViewLayer:
    """A layer in the StreamView compositing stack.

    Each layer has one source (stream, URL, or static Image) and can have
    its own target FPS and optional filter pipeline.

    For multi-output streams, multiple layers can share the same stream
    with different stream_output keys.

    Attributes:
        id: Unique layer identifier
        z_index: Stacking order (higher = on top)
        target_fps: Desired update rate for this layer
        pipeline: Optional FilterPipeline to apply to frames
        stream: Dynamic ImageStream source
        stream_output: Output key for multi-output streams
        url: Static URL or data URL
        image: Static Image object
        buffer_size: Number of frames to buffer ahead
        jpeg_quality: JPEG encoding quality (1-100)
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    z_index: int = 0
    target_fps: int = 60
    pipeline: "FilterPipeline | None" = None

    # Source - exactly ONE should be set
    stream: ImageStream | None = None
    stream_output: str | None = None  # For multi-output streams
    url: str | None = None
    image: "Image | None" = None

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
    # Anchor position for overscan layers (where the content was centered when captured)
    _anchor_x: int = field(default=0, repr=False)
    _anchor_y: int = field(default=0, repr=False)

    # Metrics
    actual_fps: float = field(default=0.0, repr=False)
    frames_produced: int = field(default=0, repr=False)
    frames_dropped: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        """Validate that exactly one source is set (unless piggyback mode)."""
        sources = [self.stream, self.url, self.image]
        active_sources = sum(1 for s in sources if s is not None)

        # Piggyback layers receive frames via inject_frame(), no source needed
        if self.piggyback:
            if active_sources > 1:
                raise ValueError("Piggyback layer can have at most one source type")
            return

        if active_sources == 0:
            raise ValueError("StreamViewLayer requires a source (stream, url, or image)")
        if active_sources > 1:
            raise ValueError("StreamViewLayer can only have one source type")

    @property
    def is_static(self) -> bool:
        """Whether this layer has a static (non-streaming) source."""
        return self.url is not None or self.image is not None

    @property
    def source_type(self) -> str:
        """Return the type of source ('stream', 'url', or 'image')."""
        if self.stream is not None:
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
        """Stop the layer's frame production."""
        self._running = False

        if self.stream is not None:
            self.stream.stop()

        if self._producer_thread is not None:
            self._producer_thread.join(timeout=1.0)
            self._producer_thread = None

    def _producer_loop(self) -> None:
        """Background thread that produces frames ahead of time."""
        frame_interval = 1.0 / self.target_fps
        next_frame_time = time.perf_counter()
        start_time = next_frame_time

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

            # Create metadata for timing tracking (may be overwritten with birth_time)
            metadata = new_frame_metadata()
            birth_time_override = None

            # Get frame from stream
            try:
                frame_result = self.stream.get_frame(timestamp)
            except Exception:
                frame_result = None

            if frame_result is None:
                # No frame available, try again
                time.sleep(0.001)
                continue

            # Handle different return types
            frame = None
            pre_encoded = None  # Pre-encoded base64 data (bypasses encoding)

            # Check for tuple[Image, float, dict, str] - frame with pre-encoded data
            if isinstance(frame_result, tuple) and len(frame_result) == 4:
                frame, birth_time_override, step_timings, pre_encoded = frame_result
                metadata.capture_time = birth_time_override * 1000
                for step_name, duration_ms in step_timings.items():
                    display_name = step_name.replace('_ms', '').capitalize()
                    metadata.add_filter_timing(display_name, 0, duration_ms)
            # Check for tuple[Image, float, dict] - frame with birth timestamp and step timings
            elif isinstance(frame_result, tuple) and len(frame_result) == 3:
                frame, birth_time_override, step_timings = frame_result
                # Override capture_time with the original birth time (convert to ms)
                metadata.capture_time = birth_time_override * 1000
                # Add step timings as filter_timings for visualization
                for step_name, duration_ms in step_timings.items():
                    # Convert step_name like 'fetch_ms' to 'Fetch'
                    display_name = step_name.replace('_ms', '').capitalize()
                    metadata.add_filter_timing(display_name, 0, duration_ms)  # relative timing
            # Check for tuple[Image, float] - frame with birth timestamp only
            elif isinstance(frame_result, tuple) and len(frame_result) == 2:
                frame, birth_time_override = frame_result
                # Override capture_time with the original birth time (convert to ms)
                metadata.capture_time = birth_time_override * 1000
            # Handle multi-output streams (dict)
            elif isinstance(frame_result, dict):
                if self.stream_output is None:
                    # Use first output
                    frame = next(iter(frame_result.values()))
                else:
                    frame = frame_result.get(self.stream_output)
                    if frame is None:
                        continue
            else:
                # Single Image
                frame = frame_result

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

            # Encode frame (or use pre-encoded data)
            metadata.encode_start = FrameMetadata.now_ms()
            if pre_encoded is not None:
                # Use pre-encoded data - skip encoding entirely
                encoded = pre_encoded
                metadata.encode_end = metadata.encode_start  # No encoding time
            else:
                try:
                    if self.use_png:
                        img_bytes = frame.to_png()
                        mime_type = "png"
                    else:
                        img_bytes = frame.to_jpeg(quality=self.jpeg_quality)
                        mime_type = "jpeg"
                    if img_bytes is None:
                        continue
                    encoded = f"data:image/{mime_type};base64," + base64.b64encode(img_bytes).decode("ascii")
                except Exception:
                    continue
                metadata.encode_end = FrameMetadata.now_ms()
            metadata.send_time = FrameMetadata.now_ms()

            # Add to buffer with metadata
            with self._lock:
                self._frame_buffer.append((timestamp, encoded, metadata))
                self.frames_produced += 1

            # Calculate timing for next frame
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

        # Add anchor position for overscan layers
        if anchor_x is not None and anchor_y is not None:
            metadata.anchor_x = anchor_x
            metadata.anchor_y = anchor_y
            # Also store in layer for reference
            self._anchor_x = anchor_x
            self._anchor_y = anchor_y

        # Inject directly into buffer
        timestamp = time.perf_counter()
        with self._lock:
            # In piggyback mode with buffer_size=1, replace existing frame
            if self.piggyback and self.buffer_size == 1 and self._frame_buffer:
                self._frame_buffer.clear()
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


def _get_cv2():
    """Get OpenCV module, returning None if not available."""
    try:
        import cv2

        return cv2
    except ImportError:
        return None
