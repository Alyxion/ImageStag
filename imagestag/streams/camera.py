"""Camera/webcam stream implementation.

This module provides CameraStream for live camera capture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .decoder import DecoderStream

if TYPE_CHECKING:
    from imagestag import Image


def _get_cv2():
    """Get OpenCV module, returning None if not available."""
    try:
        import cv2
        return cv2
    except ImportError:
        return None


class CameraStream(DecoderStream):
    """Live camera/webcam capture.

    Captures frames from a camera device. Unlike VideoStream, cameras
    have no duration and cannot be seeked. Pausing a camera stream
    stops reading frames and buffers the last captured frame.

    Example:
        stream = CameraStream(0)  # Device 0 (usually built-in webcam)
        stream.start()

        while stream.is_running:
            frame, index = stream.get_frame(stream.elapsed_time)
            if frame is not None:
                display(frame)

        stream.stop()

    Attributes:
        device: Camera device index (0, 1, etc.)
    """

    def __init__(
        self,
        device: int = 0,
        *,
        target_fps: float | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Initialize camera stream.

        :param device: Camera device index (0 = first camera)
        :param target_fps: Target frame rate (None = camera default)
        :param width: Requested capture width (None = camera default)
        :param height: Requested capture height (None = camera default)
        """
        super().__init__()
        self._device = device
        self._target_fps = target_fps
        self._requested_width = width
        self._requested_height = height
        self._cap = None
        self._source_fps: float = 30.0
        self._actual_width: int = 0
        self._actual_height: int = 0

    def start(self) -> None:
        """Open the camera capture."""
        # If already running, don't reset
        if self._running and self._cap is not None and self._cap.isOpened():
            return

        cv2 = _get_cv2()
        if cv2 is None:
            raise RuntimeError("OpenCV (cv2) is required for CameraStream")

        # Only open capture if not already open
        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self._device)
            if not self._cap.isOpened():
                raise RuntimeError(f"Failed to open camera device: {self._device}")

            # Set requested resolution if specified
            if self._requested_width is not None:
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._requested_width)
            if self._requested_height is not None:
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._requested_height)

            # Set target FPS if specified
            if self._target_fps is not None:
                self._cap.set(cv2.CAP_PROP_FPS, self._target_fps)

            # Get actual properties
            self._source_fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
            self._actual_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._actual_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        super().start()

    def stop(self) -> None:
        """Release the camera capture."""
        super().stop()
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None

    def get_frame(self, timestamp: float) -> tuple["Image | None", int]:
        """Read the next frame from the camera.

        When paused, returns (None, current_index) - the last frame
        is still available via the last_frame property.

        :param timestamp: Timestamp from caller (not used for cameras)
        :return: Tuple of (frame, frame_index)
        """
        from imagestag import Image

        # Return None when paused (last_frame property still available)
        if self._paused:
            return (None, self._frame_index)

        if not self._running:
            return (None, self._frame_index)

        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                return (None, self._frame_index)

            cv2 = _get_cv2()

            ret, frame = self._cap.read()
            if not ret:
                return (None, self._frame_index)

            # Convert BGR (OpenCV default) to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = Image(frame_rgb, pixel_format="RGB")

            # Store frame and return with new index
            new_index = self._store_frame(result)
            return (result, new_index)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def device(self) -> int:
        """Camera device index."""
        return self._device

    @property
    def fps(self) -> float:
        """Camera frame rate."""
        return self._target_fps or self._source_fps

    @property
    def width(self) -> int:
        """Actual capture width in pixels."""
        return self._actual_width

    @property
    def height(self) -> int:
        """Actual capture height in pixels."""
        return self._actual_height

    @property
    def has_duration(self) -> bool:
        """Cameras have no duration (infinite stream)."""
        return False

    @property
    def is_seekable(self) -> bool:
        """Cameras cannot be seeked."""
        return False
