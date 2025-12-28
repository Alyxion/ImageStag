"""Shared playback controller for video players.

This module provides common playback logic that can be used by any
video player implementation (pygame, tkinter, kivy, ASCII, etc.).

Example:
    from imagestag.components.shared import PlaybackController, PlaybackConfig
    from imagestag.streams import VideoStream

    video = VideoStream("movie.mp4")
    config = PlaybackConfig()
    controller = PlaybackController(video, config)

    controller.play()
    print(f"Position: {controller.current_time:.1f}s")
    controller.seek_to(30.0)
    controller.pause()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from imagestag.streams import VideoStream


class PlaybackState(Enum):
    """Playback state machine."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    SEEKING = "seeking"


@dataclass
class PlaybackConfig:
    """Configuration for video playback controls."""

    # Speed options
    speed_options: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0)
    default_speed: float = 1.0

    # Seek settings
    seek_step: float = 5.0  # Seconds per seek step
    fine_seek_step: float = 1.0  # Seconds for fine seeking

    # UI settings
    show_progress_bar: bool = True
    show_time: bool = True
    show_speed: bool = True
    show_fps: bool = True


@dataclass
class ProgressState:
    """Current state for progress bar rendering."""

    current_time: float = 0.0
    total_time: float = 0.0
    cursor_position: float | None = None  # 0.0-1.0 when seeking
    is_seeking: bool = False
    playback_speed: float = 1.0
    actual_fps: float = 0.0
    playback_state: PlaybackState = PlaybackState.STOPPED


class PlaybackController:
    """Control video playback with speed adjustment and seeking.

    This controller wraps a VideoStream and provides a high-level interface
    for play/pause, seeking, and speed control. It can be used by any
    video player implementation.

    Example:
        controller = PlaybackController(video, config)
        controller.play()

        # In main loop:
        frame, idx = controller.get_frame()
        if frame:
            display(frame)

        # Handle user input:
        controller.toggle()  # Play/pause
        controller.seek_relative(5.0)  # Forward 5 seconds
        controller.adjust_speed(0.25)  # Speed up
    """

    def __init__(
        self,
        video: "VideoStream",
        config: PlaybackConfig | None = None,
    ):
        """Initialize playback controller.

        :param video: VideoStream to control
        :param config: Playback configuration (uses defaults if None)
        """
        self.video = video
        self.config = config or PlaybackConfig()
        self._state = PlaybackState.STOPPED
        self._speed = self.config.default_speed
        self._pause_position: float = 0.0

        # Seeking state
        self._seek_mode = False
        self._seek_cursor: float | None = None
        self._seek_original_position: float = 0.0

        # FPS tracking
        self._fps_times: list[float] = []

        # Callbacks
        self._on_state_change: list[Callable[[PlaybackState], None]] = []

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def state(self) -> PlaybackState:
        """Current playback state."""
        return self._state

    @property
    def speed(self) -> float:
        """Current playback speed multiplier."""
        return self._speed

    @property
    def playback_speed(self) -> float:
        """Alias for speed property."""
        return self._speed

    @property
    def current_time(self) -> float:
        """Current playback position in seconds."""
        if self._state == PlaybackState.STOPPED:
            return 0.0
        if self._state == PlaybackState.PAUSED:
            return self._pause_position
        return self.video.current_position

    @property
    def duration(self) -> float:
        """Total video duration in seconds."""
        return self.video.duration

    @property
    def progress(self) -> float:
        """Current progress as 0.0-1.0."""
        if self.duration > 0:
            return self.current_time / self.duration
        return 0.0

    @property
    def is_playing(self) -> bool:
        """Whether currently playing."""
        return self._state == PlaybackState.PLAYING

    @property
    def is_paused(self) -> bool:
        """Whether currently paused."""
        return self._state == PlaybackState.PAUSED

    @property
    def is_seeking(self) -> bool:
        """Whether in seek mode."""
        return self._seek_mode

    @property
    def seek_cursor(self) -> float | None:
        """Current seek cursor position (0.0-1.0) or None."""
        return self._seek_cursor

    @property
    def fps(self) -> float:
        """Current actual FPS."""
        now = time.time()
        self._fps_times = [t for t in self._fps_times if now - t < 1.0]
        return float(len(self._fps_times))

    # -------------------------------------------------------------------------
    # Playback Control
    # -------------------------------------------------------------------------

    def play(self) -> None:
        """Start or resume playback."""
        if self._state == PlaybackState.STOPPED:
            self.video.start()
        elif self._state == PlaybackState.PAUSED:
            self.video.resume()
        self._set_state(PlaybackState.PLAYING)

    def pause(self) -> None:
        """Pause playback."""
        if self._state == PlaybackState.PLAYING:
            self._pause_position = self.video.current_position
            self.video.pause()
            self._set_state(PlaybackState.PAUSED)

    def toggle(self) -> None:
        """Toggle between play and pause."""
        if self._state == PlaybackState.PLAYING:
            self.pause()
        elif self._state in (PlaybackState.PAUSED, PlaybackState.STOPPED):
            self.play()

    def stop(self) -> None:
        """Stop playback completely."""
        self.video.stop()
        self._set_state(PlaybackState.STOPPED)

    # -------------------------------------------------------------------------
    # Seeking
    # -------------------------------------------------------------------------

    def seek_to(self, position: float) -> None:
        """Seek to absolute position in seconds."""
        position = max(0.0, min(position, self.duration))
        self.video.seek_to(position)
        if self._state == PlaybackState.PAUSED:
            self._pause_position = position

    def seek_relative(self, delta: float) -> None:
        """Seek relative to current position."""
        self.seek_to(self.current_time + delta)

    def seek_forward(self) -> None:
        """Seek forward by configured step."""
        self.seek_relative(self.config.seek_step)

    def seek_backward(self) -> None:
        """Seek backward by configured step."""
        self.seek_relative(-self.config.seek_step)

    def seek_to_start(self) -> None:
        """Seek to start of video."""
        self.seek_to(0.0)

    def seek_to_end(self) -> None:
        """Seek to near end of video."""
        self.seek_to(max(0.0, self.duration - 0.1))

    # -------------------------------------------------------------------------
    # Seek Mode (cursor-based seeking)
    # -------------------------------------------------------------------------

    def enter_seek_mode(self) -> None:
        """Enter interactive seek mode."""
        self._seek_mode = True
        self._seek_original_position = self.current_time
        if self.duration > 0:
            self._seek_cursor = self.current_time / self.duration
        else:
            self._seek_cursor = 0.0

    def exit_seek_mode(self, confirm: bool = True) -> None:
        """Exit seek mode.

        :param confirm: If True, seek to cursor position. If False, restore original.
        """
        if not self._seek_mode:
            return

        if confirm and self._seek_cursor is not None:
            self.seek_to(self._seek_cursor * self.duration)
        else:
            self.seek_to(self._seek_original_position)

        self._seek_mode = False
        self._seek_cursor = None

    def move_seek_cursor(self, delta: float) -> None:
        """Move seek cursor by delta (0.0-1.0 range).

        :param delta: Amount to move cursor (e.g., 0.01 = 1%)
        """
        if self._seek_cursor is not None:
            self._seek_cursor = max(0.0, min(1.0, self._seek_cursor + delta))

    # -------------------------------------------------------------------------
    # Speed Control
    # -------------------------------------------------------------------------

    def set_speed(self, multiplier: float) -> None:
        """Set playback speed."""
        self._speed = max(0.1, min(8.0, multiplier))
        # Note: Speed control would require VideoStream support

    def adjust_speed(self, delta: float) -> None:
        """Adjust speed by delta, snapping to nearest config option."""
        current = self._speed
        options = sorted(self.config.speed_options)

        if delta > 0:
            for opt in options:
                if opt > current + 0.01:
                    self.set_speed(opt)
                    return
        else:
            for opt in reversed(options):
                if opt < current - 0.01:
                    self.set_speed(opt)
                    return

    def speed_up(self) -> None:
        """Increase speed to next option."""
        self.adjust_speed(0.25)

    def speed_down(self) -> None:
        """Decrease speed to previous option."""
        self.adjust_speed(-0.25)

    # -------------------------------------------------------------------------
    # Frame Access
    # -------------------------------------------------------------------------

    def get_frame(self):
        """Get current frame from video.

        :return: Tuple of (frame, index) or (None, index)
        """
        if self._state == PlaybackState.STOPPED:
            return (None, -1)

        frame, idx = self.video.get_frame(self.current_time)

        # Track FPS
        if frame is not None:
            self._fps_times.append(time.time())

        return (frame, idx)

    def update_fps(self) -> float:
        """Update and return current FPS."""
        now = time.time()
        self._fps_times.append(now)
        self._fps_times = [t for t in self._fps_times if now - t < 1.0]
        return float(len(self._fps_times))

    # -------------------------------------------------------------------------
    # Progress State
    # -------------------------------------------------------------------------

    def get_progress_state(self) -> ProgressState:
        """Get current state for progress bar rendering."""
        return ProgressState(
            current_time=self.current_time,
            total_time=self.duration,
            cursor_position=self._seek_cursor,
            is_seeking=self._seek_mode,
            playback_speed=self._speed,
            actual_fps=self.fps,
            playback_state=self._state,
        )

    # -------------------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------------------

    def on_state_change(self, callback: Callable[[PlaybackState], None]) -> None:
        """Register a callback for state changes."""
        self._on_state_change.append(callback)

    def _set_state(self, state: PlaybackState) -> None:
        """Set state and notify callbacks."""
        old_state = self._state
        self._state = state
        if old_state != state:
            for callback in self._on_state_change:
                callback(state)


def format_time(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    if seconds < 0:
        seconds = 0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
