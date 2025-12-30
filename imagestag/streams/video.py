"""Video file stream implementation.

This module provides VideoStream for playing video files with seeking support.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from .decoder import DecoderStream

if TYPE_CHECKING:
    from imagestag import Image


# Cache modules at module level to avoid import overhead in hot loops
_cv2_module = None
_Image_class = None


def _get_cv2():
    """Get OpenCV module, returning None if not available."""
    global _cv2_module
    if _cv2_module is not None:
        return _cv2_module
    try:
        import cv2
        _cv2_module = cv2
        return cv2
    except ImportError:
        return None


def _get_Image():
    """Get Image class, caching to avoid import overhead."""
    global _Image_class
    if _Image_class is not None:
        return _Image_class
    from imagestag import Image
    _Image_class = Image
    return Image


class VideoStream(DecoderStream):
    """Video file playback with seeking support.

    Plays video files from disk with timestamp-based frame seeking to
    maintain correct playback speed. Supports looping and seeking.

    Example:
        stream = VideoStream('/path/to/video.mp4', loop=True)
        stream.start()

        # Get frames synchronized to playback time
        while stream.is_running:
            frame, index = stream.get_frame(stream.elapsed_time)
            if frame is not None:
                display(frame)

        # Seek to a specific position
        stream.seek_to(10.0)  # Jump to 10 seconds

        stream.stop()

    Attributes:
        loop: Whether to loop when video ends
        frame_count: Total number of frames in the video
    """

    def __init__(
        self,
        path: str,
        *,
        loop: bool = True,
        target_fps: float | None = None,
        max_fps: float | None = 60.0,
        preserve_source_fps: bool = True,
    ) -> None:
        """Initialize video stream.

        :param path: Path to video file
        :param loop: Whether to loop video when it ends
        :param target_fps: Target frame rate (None = use source fps)
        :param max_fps: Maximum output fps in real time (default: 60.0, None = unlimited)
        :param preserve_source_fps: If True (default), limit output to source_fps * speed.
            At 1x speed with 24fps source, produce max 24fps.
            At 3x speed with 24fps source, produce max 72fps (or max_fps if lower).
            If False, always produce at max_fps when frames are available.
        """
        super().__init__()
        self._path = path
        self._loop = loop
        self._target_fps = target_fps
        self._max_fps = max_fps
        self._preserve_source_fps = preserve_source_fps
        self._cap = None
        self._source_fps: float = 30.0
        self._frame_count: int = 0
        self._last_decoded_index: int = -1
        self._last_output_time: float = 0.0  # For rate limiting

        # Video dimensions (available after reading metadata)
        self._width: int = 0
        self._height: int = 0

        # Pre-read source FPS and dimensions from video file (so it's available before start())
        cv2 = _get_cv2()
        if cv2 is not None:
            try:
                cap = cv2.VideoCapture(self._path)
                if cap.isOpened():
                    self._source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                    self._frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    self._width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    self._height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()
            except Exception:
                pass  # Keep defaults

    def start(self) -> None:
        """Open the video capture."""
        # If already running, don't reset
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
            self._last_decoded_index = -1

        super().start()

    def stop(self) -> None:
        """Release the video capture."""
        super().stop()
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None

    def seek_to(self, seconds: float) -> None:
        """Seek to a specific position in the video.

        :param seconds: Target position in seconds from the start
        """
        # Clamp to valid range
        if self._frame_count > 0 and self._source_fps > 0:
            max_time = self._frame_count / self._source_fps
            seconds = max(0.0, min(seconds, max_time))

        # Adjust timing so elapsed calculation gives us the target position
        # We need to modify _start_time and _accumulated_pause appropriately
        now = time.perf_counter()

        # Reset timing: new_start_time + accumulated_pause = now - seconds
        # If paused, we also need to update _pause_time
        if self._paused:
            # When paused: elapsed = pause_time - start_time - accumulated_pause
            # We want: seconds = pause_time - new_start_time - new_accumulated_pause
            # Keep accumulated_pause, adjust start_time
            self._start_time = self._pause_time - seconds - self._accumulated_pause
        else:
            # When running: elapsed = now - start_time - accumulated_pause
            # We want: seconds = now - new_start_time - new_accumulated_pause
            # Keep accumulated_pause, adjust start_time
            self._start_time = now - seconds - self._accumulated_pause

        # Reset frame index to force a seek on next get_frame
        self._last_decoded_index = -1

    def get_frame(self, timestamp: float) -> tuple["Image | None", int]:
        """Read the frame corresponding to the current playback time.

        Seeks to the correct frame based on elapsed time. Respects max_fps
        and preserve_source_fps settings for frame rate limiting.

        :param timestamp: Timestamp from caller (not used, we track our own time)
        :return: Tuple of (frame, frame_index)
        """
        Image = _get_Image()

        # Return None when paused (but don't close capture)
        if self._paused:
            return (None, self._frame_index)

        if not self._running:
            return (None, self._frame_index)

        # Rate limiting: calculate effective max fps
        now = time.perf_counter()
        effective_max_fps: float | None = None
        current_speed = self.playback_speed  # Use property to get inherited value

        if self._preserve_source_fps:
            # Limit to source fps scaled by playback speed
            effective_max_fps = self._source_fps * current_speed
            if self._max_fps is not None:
                effective_max_fps = min(effective_max_fps, self._max_fps)
        elif self._max_fps is not None:
            effective_max_fps = self._max_fps

        # Check rate limit
        if effective_max_fps is not None and effective_max_fps > 0:
            min_interval = 1.0 / effective_max_fps
            if now - self._last_output_time < min_interval:
                return (None, self._frame_index)  # Rate limited

        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                return (None, self._frame_index)

            cv2 = _get_cv2()

            # Calculate which frame we should be showing
            elapsed = self.elapsed_time
            target_frame = int(elapsed * self._source_fps)

            # Handle looping
            if self._frame_count > 0:
                if target_frame >= self._frame_count:
                    if self._loop:
                        # Loop: just wrap the frame number, don't modify timing
                        # This ensures smooth looping without timing drift
                        target_frame = target_frame % self._frame_count
                    else:
                        return (None, self._frame_index)  # Video ended

            # Only read if we need a new frame
            if target_frame == self._last_decoded_index:
                return (None, self._frame_index)  # Same frame, skip

            # Seek strategy: sequential reads are ~10x faster than seeks
            # Only seek if we're going backwards or significantly ahead
            current_pos = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
            frames_ahead = target_frame - current_pos

            if frames_ahead < 0 or frames_ahead > 5:
                # Need to seek: going backwards or too far ahead
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, frame = self._cap.read()
            elif frames_ahead == 0:
                # Already at right position, just read
                ret, frame = self._cap.read()
            else:
                # Slightly behind (1-5 frames): sequential reads to catch up
                # This is faster than seeking for small gaps
                ret = True
                frame = None
                for _ in range(frames_ahead + 1):
                    ret, frame = self._cap.read()
                    if not ret:
                        break

            if not ret:
                if self._loop and self._frame_count > 0:
                    # Loop back to start
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    # Reset timing
                    now = time.perf_counter()
                    self._start_time = now
                    self._accumulated_pause = 0.0
                    self._last_decoded_index = -1

                    ret, frame = self._cap.read()
                    if not ret:
                        return (None, self._frame_index)
                    target_frame = 0
                else:
                    return (None, self._frame_index)

            # Track which frame we just read
            self._last_decoded_index = target_frame

            # Validate frame data - detect corrupted/blank frames
            # Check if frame is mostly white (corrupted) or empty
            if frame is None or frame.size == 0:
                return (None, self._frame_index)

            # Quick check: sample a few pixels to detect all-white or all-black frames
            # This catches common video decode errors that produce solid color frames
            h, w = frame.shape[:2]
            if h > 10 and w > 10:
                # Sample center region
                sample = frame[h//4:3*h//4, w//4:3*w//4]
                mean_val = sample.mean()
                # If nearly all white (>250) or all black (<5), likely corrupted
                if mean_val > 250:
                    # Corrupted white frame - skip and return previous
                    return (None, self._frame_index)

            # Convert BGR (OpenCV default) to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = Image(frame_rgb, pixel_format="RGB")

            # Update rate limit timestamp
            self._last_output_time = time.perf_counter()

            # Store frame and return with new index
            new_index = self._store_frame(result)
            return (result, new_index)

    def grab_frame_by_index(self, frame_index: int) -> "Image | None":
        """Convenience method to get a frame by index (ignoring global index).

        :param frame_index: Frame number (0-based)
        :return: Image or None
        """
        frame, _ = self.get_frame_by_index(frame_index)
        return frame

    def get_frame_by_index(self, frame_index: int) -> tuple["Image | None", int]:
        """Get a specific frame by its index in the video.

        Unlike get_frame(timestamp), this directly seeks to the frame number.
        Useful for random access or frame-by-frame processing.

        :param frame_index: Frame number (0-based, must be < frame_count)
        :return: Tuple of (frame, global_frame_index)
        """
        Image = _get_Image()

        if not self._running:
            return (None, self._frame_index)

        # Clamp to valid range
        if self._frame_count > 0:
            frame_index = max(0, min(frame_index, self._frame_count - 1))

        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                return (None, self._frame_index)

            cv2 = _get_cv2()

            # Seek to the requested frame
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

            ret, frame = self._cap.read()
            if not ret:
                return (None, self._frame_index)

            # Track which frame we just read
            self._last_decoded_index = frame_index

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
    def loop(self) -> bool:
        """Whether the video loops when it ends."""
        return self._loop

    @loop.setter
    def loop(self, value: bool) -> None:
        """Set whether the video loops when it ends."""
        self._loop = value

    @property
    def max_fps(self) -> float | None:
        """Maximum output fps in real time (None = unlimited)."""
        return self._max_fps

    @max_fps.setter
    def max_fps(self, value: float | None) -> None:
        """Set maximum output fps."""
        self._max_fps = value

    @property
    def preserve_source_fps(self) -> bool:
        """Whether to limit output to source_fps * playback_speed."""
        return self._preserve_source_fps

    @preserve_source_fps.setter
    def preserve_source_fps(self, value: bool) -> None:
        """Set whether to preserve source fps."""
        self._preserve_source_fps = value

    @property
    def source_fps(self) -> float:
        """Original frame rate of the video file."""
        return self._source_fps

    @property
    def fps(self) -> float:
        """Source frame rate."""
        return self._target_fps or self._source_fps

    @property
    def frame_count(self) -> int:
        """Total number of frames in the video."""
        return self._frame_count

    @property
    def has_duration(self) -> bool:
        """Videos have known duration."""
        return True

    @property
    def is_seekable(self) -> bool:
        """Videos support seeking."""
        return True

    @property
    def duration(self) -> float:
        """Total video duration in seconds."""
        if self._frame_count > 0 and self._source_fps > 0:
            return self._frame_count / self._source_fps
        return 0.0

    @property
    def current_position(self) -> float:
        """Current playback position in seconds.

        When looping is enabled, this returns the position within the current loop
        (wraps around to 0 after reaching the end).
        """
        elapsed = self.elapsed_time
        duration = self.duration
        if self._loop and duration > 0 and elapsed > duration:
            return elapsed % duration
        return elapsed

    @property
    def width(self) -> int:
        """Video frame width in pixels."""
        return self._width

    @property
    def height(self) -> int:
        """Video frame height in pixels."""
        return self._height

    @property
    def aspect_ratio(self) -> float:
        """Video aspect ratio (width / height)."""
        if self._height > 0:
            return self._width / self._height
        return 16 / 9  # Default fallback
