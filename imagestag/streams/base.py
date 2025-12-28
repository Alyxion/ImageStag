"""Base stream classes for ImageStag.

This module defines the core ImageStream abstract base class that provides
frame tracking, lifecycle management, pause/resume, and subscriber notifications.
"""

from __future__ import annotations

import concurrent.futures
import threading
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Literal

if TYPE_CHECKING:
    from imagestag import Image


# Type alias for frame callback return types
# Can return:
#   - Image: single frame
#   - dict[str, Image]: multi-output streams
#   - tuple[Image, float]: frame with birth timestamp (for frame sharing)
#   - tuple[Image, float, dict]: frame with birth timestamp and step timings
#   - tuple[Image, float, dict, str]: frame with timestamp, timings, and pre-encoded
#   - None: no frame available
FrameResult = "Image | dict[str, Image] | tuple | None"


class ImageStream(ABC):
    """Base class for all frame sources.

    Provides frame tracking, lifecycle management, pause/resume functionality,
    and subscriber notifications. Subclasses must implement get_frame() to
    provide frames on demand.

    The stream operates with a frame index system that allows consumers to
    efficiently detect new frames without timestamp comparison.

    Attributes:
        _running: Whether the stream is currently running
        _paused: Whether the stream is paused
        _start_time: perf_counter when started
        _pause_time: perf_counter when paused (0 if not paused)
        _accumulated_pause: Total pause time to subtract from elapsed
        _frame_index: Monotonically increasing frame counter
        _last_frame: Most recently produced frame
        _last_frame_timestamp: Capture timestamp of last frame
        _mode: Execution mode for get_frame calls

    Example:
        class MyStream(ImageStream):
            def get_frame(self, timestamp: float) -> tuple[Image | None, int]:
                frame = self._generate_frame(timestamp)
                if frame is not None:
                    return (frame, self._store_frame(frame))
                return (None, self._frame_index)

        stream = MyStream()
        stream.start()

        # Consumer pattern
        last_index = -1
        while stream.is_running:
            frame, index = stream.get_frame(stream.elapsed_time)
            if index != last_index:
                process(frame)
                last_index = index
    """

    def __init__(self) -> None:
        """Initialize the stream with default state."""
        # Lifecycle state
        self._running: bool = False
        self._paused: bool = False
        self._start_time: float = 0.0
        self._pause_time: float = 0.0
        self._accumulated_pause: float = 0.0
        self._mode: Literal["sync", "async", "thread"] = "thread"

        # Frame tracking
        self._frame_index: int = 0
        self._last_frame: "Image | None" = None
        self._last_frame_timestamp: float = 0.0
        self._last_frame_lock = threading.Lock()

        # Subscriber notifications
        self._frame_subscribers: list[threading.Event] = []
        self._on_frame_callbacks: list[Callable[["Image", float], None]] = []
        self._callback_executor: concurrent.futures.ThreadPoolExecutor | None = None

    @abstractmethod
    def get_frame(self, timestamp: float) -> tuple["Image | None", int]:
        """Get a frame at the given timestamp.

        Returns a tuple of (frame, frame_index) where:
        - (Image, new_index) if a new frame is available
        - (None, current_index) if no new frame (reuse last frame)

        The frame_index is a monotonically increasing counter that increments
        each time a new frame is produced. Consumers can compare indices to
        detect new frames efficiently.

        :param timestamp: Current playback time in seconds
        :return: Tuple of (frame or None, frame_index)
        """
        ...

    def grab_frame(self, timestamp: float = 0.0) -> "Image | None":
        """Convenience method to get just the frame (ignoring index).

        Useful for simple one-off frame grabs.

        :param timestamp: Playback time in seconds (default: 0.0)
        :return: Image or None
        """
        frame, _ = self.get_frame(timestamp)
        return frame

    # -------------------------------------------------------------------------
    # Lifecycle Methods
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start the stream.

        Sets the running flag and records start time. Subclasses should
        call super().start() and then initialize their specific resources.
        """
        if self._running:
            return

        self._running = True
        self._paused = False
        self._start_time = time.perf_counter()
        self._pause_time = 0.0
        self._accumulated_pause = 0.0

    def stop(self) -> None:
        """Stop the stream.

        Sets the running flag to False. Subclasses should call super().stop()
        and then cleanup their specific resources.
        """
        self._running = False
        self._paused = False

        # Shutdown callback executor if created
        if self._callback_executor is not None:
            self._callback_executor.shutdown(wait=False)
            self._callback_executor = None

    def pause(self) -> None:
        """Pause the stream.

        Pausing preserves the current position for resume. The stream
        will return None for get_frame() calls while paused.
        """
        if self._running and not self._paused:
            self._paused = True
            self._pause_time = time.perf_counter()

    def resume(self) -> None:
        """Resume the stream from paused state.

        Adjusts timing so that elapsed_time continues from where it paused.
        """
        if self._paused and self._pause_time > 0.0:
            # Calculate how long we were paused
            pause_duration = time.perf_counter() - self._pause_time
            self._accumulated_pause += pause_duration
            self._pause_time = 0.0
            self._paused = False

    def toggle_pause(self) -> None:
        """Toggle between paused and running state."""
        if self._paused:
            self.resume()
        else:
            self.pause()

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def mode(self) -> Literal["sync", "async", "thread"]:
        """Execution mode for get_frame calls."""
        return self._mode

    @property
    def is_running(self) -> bool:
        """Whether the stream is currently running (not stopped)."""
        return self._running

    @property
    def is_paused(self) -> bool:
        """Whether the stream is currently paused."""
        return self._paused

    @property
    def elapsed_time(self) -> float:
        """Seconds since start, accounting for pauses.

        If paused, returns the time at which pause occurred.
        """
        if not self._running and self._start_time == 0.0:
            return 0.0

        if self._paused:
            # Return time when paused
            return self._pause_time - self._start_time - self._accumulated_pause

        return time.perf_counter() - self._start_time - self._accumulated_pause

    @property
    def frame_index(self) -> int:
        """Current global frame counter.

        Monotonically increasing. Compare indices to detect new frames.
        """
        return self._frame_index

    @property
    def frame_count(self) -> int:
        """Total number of frames in the stream.

        Returns 0 for infinite/unknown length streams (cameras, generators).
        Override in subclasses with known frame counts (e.g., VideoStream).
        """
        return 0

    @property
    def has_frame_count(self) -> bool:
        """Whether this stream has a known, finite frame count.

        True for video files, False for cameras and generators.
        """
        return self.frame_count > 0

    @property
    def last_frame(self) -> "Image | None":
        """Get the most recently produced frame (thread-safe).

        Use this for frame sharing - e.g., a processing stream can access
        the same frame the source is displaying.
        """
        with self._last_frame_lock:
            return self._last_frame

    @property
    def last_frame_timestamp(self) -> float:
        """Get the capture timestamp of the last frame (perf_counter seconds).

        This is the exact moment the frame was produced/captured.
        Use this to calculate true birth-to-display latency.
        """
        with self._last_frame_lock:
            return self._last_frame_timestamp

    # -------------------------------------------------------------------------
    # Frame Sharing
    # -------------------------------------------------------------------------

    def get_last_frame_with_timestamp(self) -> tuple["Image | None", float]:
        """Get the last frame and its timestamp atomically.

        :return: Tuple of (frame, capture_timestamp_seconds)
        """
        with self._last_frame_lock:
            return self._last_frame, self._last_frame_timestamp

    def subscribe(self) -> threading.Event:
        """Subscribe to frame events.

        Returns an Event that is set when a new frame arrives.
        Dependent streams can wait on this event instead of polling.

        :return: Threading Event for new frame notifications
        """
        event = threading.Event()
        self._frame_subscribers.append(event)
        return event

    def unsubscribe(self, event: threading.Event) -> None:
        """Unsubscribe from frame events.

        :param event: The event returned by subscribe()
        """
        if event in self._frame_subscribers:
            self._frame_subscribers.remove(event)

    def on_frame(self, callback: Callable[["Image", float], None]) -> None:
        """Register a callback to run when a frame is produced.

        Callbacks are run in background threads to avoid blocking
        the frame producer. Each callback gets its own thread.

        :param callback: Function(frame, capture_timestamp) to call
        """
        self._on_frame_callbacks.append(callback)

    def remove_on_frame(self, callback: Callable[["Image", float], None]) -> None:
        """Remove an on_frame callback.

        :param callback: The callback to remove
        """
        if callback in self._on_frame_callbacks:
            self._on_frame_callbacks.remove(callback)

    def wait_for_frame(self, timeout: float = 0.1) -> bool:
        """Wait for a new frame to be produced.

        :param timeout: Max time to wait in seconds
        :return: True if frame arrived, False if timeout
        """
        event = self.subscribe()
        try:
            return event.wait(timeout)
        finally:
            self.unsubscribe(event)

    # -------------------------------------------------------------------------
    # Internal Methods (for subclasses)
    # -------------------------------------------------------------------------

    def _store_frame(self, frame: "Image") -> int:
        """Store a frame, increment index, and notify subscribers.

        Subclasses should call this when they produce a new frame.
        Returns the new frame index for use in get_frame() return value.

        :param frame: The newly produced frame
        :return: The new frame index
        """
        timestamp = time.perf_counter()

        with self._last_frame_lock:
            self._frame_index += 1
            self._last_frame = frame
            self._last_frame_timestamp = timestamp

        # Notify subscribers
        self._notify_subscribers()

        # Run callbacks
        self._run_on_frame_callbacks(frame, timestamp)

        return self._frame_index

    def _notify_subscribers(self) -> None:
        """Notify all subscribers that a new frame is available."""
        for event in self._frame_subscribers:
            event.set()

    def _run_on_frame_callbacks(self, frame: "Image", timestamp: float) -> None:
        """Run all registered on_frame callbacks in background threads.

        Callbacks are run asynchronously to avoid blocking frame production.
        Each callback gets its own thread to prevent slow callbacks from
        delaying other callbacks.

        :param frame: The new frame
        :param timestamp: Capture timestamp
        """
        if not self._on_frame_callbacks:
            return

        # Create executor lazily
        if self._callback_executor is None:
            self._callback_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=4,
                thread_name_prefix="on_frame_callback",
            )

        for callback in self._on_frame_callbacks:
            self._callback_executor.submit(self._safe_callback, callback, frame, timestamp)

    def _safe_callback(
        self,
        callback: Callable[["Image", float], None],
        frame: "Image",
        timestamp: float,
    ) -> None:
        """Safely execute a callback, catching any exceptions.

        :param callback: The callback to execute
        :param frame: Frame to pass to callback
        :param timestamp: Timestamp to pass to callback
        """
        try:
            callback(frame, timestamp)
        except Exception:
            pass  # Don't let callback errors propagate
