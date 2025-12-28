"""Generator stream implementation.

This module provides GeneratorStream for procedural/on-demand frame generation.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Callable, Literal

from .base import ImageStream, FrameResult

if TYPE_CHECKING:
    from imagestag import Image


class GeneratorStream(ImageStream):
    """On-demand image generation via subclassing or callback.

    Preferred usage: Subclass and override the `render()` method to generate
    frames. Alternatively, pass a handler callback for simple cases.

    The render method (or handler) receives a timestamp and returns:
    - An Image for single-output streams
    - A dict[str, Image] for multi-output streams
    - A tuple (Image, birth_time) for frame sharing with timing
    - A tuple (Image, birth_time, step_timings) with processing metrics
    - None to skip the frame

    Example (class-based - preferred):
        class GradientStream(GeneratorStream):
            def __init__(self, width: int, height: int):
                super().__init__()
                self.width = width
                self.height = height

            def render(self, timestamp: float) -> Image:
                # Generate animated gradient
                pixels = create_gradient(self.width, self.height, timestamp)
                return Image(pixels, pixel_format='RGB')

        stream = GradientStream(640, 480)

    Example (callback-based - for simple cases):
        stream = GeneratorStream(lambda t: generate_noise(t))

    Example (dependent stream - processes frames from source):
        class ThermalStream(GeneratorStream):
            def render(self, timestamp: float) -> Image:
                frame = self.source.last_frame
                if frame is not None:
                    return apply_thermal_filter(frame)
                return None

        thermal = ThermalStream(source=camera_stream)

    Attributes:
        source: Optional source stream for synchronized processing
    """

    def __init__(
        self,
        handler: Callable[[float], FrameResult] | None = None,
        mode: Literal["sync", "async", "thread"] = "thread",
        source: ImageStream | None = None,
    ) -> None:
        """Initialize generator stream.

        :param handler: Optional callable that takes timestamp and returns Image(s).
                       If not provided, override the render() method instead.
        :param mode: Execution mode ('sync', 'async', 'thread')
        :param source: Optional source stream to depend on (for frame-synced processing)
        """
        super().__init__()
        self._handler = handler
        self._mode = mode
        self._source = source
        self._last_result: FrameResult = None
        self._last_source_index: int = -1
        self._processing_lock = threading.Lock()

    def render(self, timestamp: float) -> FrameResult:
        """Generate a frame for the given timestamp.

        Override this method in subclasses to implement custom frame generation.
        The default implementation calls the handler callback if provided.

        :param timestamp: Current playback time in seconds
        :return: Image, dict of Images, tuple with timing info, or None
        """
        if self._handler is not None:
            return self._handler(timestamp)
        return None

    def get_frame(self, timestamp: float) -> tuple["Image | None", int]:
        """Call render() to generate a frame.

        If source is set, only processes when source has a new frame.
        Returns cached result if source hasn't updated.

        :param timestamp: Current playback time in seconds
        :return: Tuple of (frame, frame_index)
        """
        # Return None when paused
        if self._paused:
            return (None, self._frame_index)

        if self._source is not None:
            # Check if source has a new frame by comparing indices
            source_index = self._source.frame_index
            if source_index == self._last_source_index and self._last_result is not None:
                # Return cached result - source hasn't updated
                return self._extract_frame_from_result(self._last_result)

            # Process new frame from source
            with self._processing_lock:
                self._last_source_index = source_index
                result = self.render(timestamp)
                self._last_result = result
                return self._process_result(result)

        # No source dependency - just call render
        result = self.render(timestamp)
        return self._process_result(result)

    def _process_result(self, result: FrameResult) -> tuple["Image | None", int]:
        """Process handler result and store frame if valid.

        :param result: Result from handler
        :return: Tuple of (frame, frame_index)
        """
        if result is None:
            return (None, self._frame_index)

        # Extract frame from various result types
        frame = self._extract_frame(result)

        if frame is not None:
            new_index = self._store_frame(frame)
            return (frame, new_index)

        return (None, self._frame_index)

    def _extract_frame_from_result(
        self, result: FrameResult
    ) -> tuple["Image | None", int]:
        """Extract frame from cached result without storing.

        :param result: Cached result
        :return: Tuple of (frame, current_frame_index)
        """
        frame = self._extract_frame(result)
        return (frame, self._frame_index)

    def _extract_frame(self, result: FrameResult) -> "Image | None":
        """Extract frame from various result types.

        :param result: Handler result
        :return: Image or None
        """
        if result is None:
            return None

        # Check for tuple[Image, float, dict, str] - frame with pre-encoded
        if isinstance(result, tuple) and len(result) == 4:
            return result[0]

        # Check for tuple[Image, float, dict] - frame with timestamp and timings
        if isinstance(result, tuple) and len(result) == 3:
            return result[0]

        # Check for tuple[Image, float] - frame with timestamp
        if isinstance(result, tuple) and len(result) == 2:
            return result[0]

        # Handle dict (multi-output) - return first value
        if isinstance(result, dict):
            values = list(result.values())
            return values[0] if values else None

        # Single Image
        return result

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def source(self) -> ImageStream | None:
        """The source stream this depends on."""
        return self._source

    @property
    def has_source(self) -> bool:
        """Whether this stream has a source dependency."""
        return self._source is not None


# Backwards compatibility alias
CustomStream = GeneratorStream
