"""
ASCII Video Player Component - Interactive terminal-based video player.

A reusable component for playing videos as colored ASCII art in the terminal
with full keyboard controls for play/pause, seeking, speed control, and more.

Example:
    from imagestag.components.ascii import AsciiPlayer, AsciiPlayerConfig

    # Simple usage
    player = AsciiPlayer("video.mp4")
    player.play()

    # With custom configuration
    config = AsciiPlayerConfig(
        show_progress_bar=True,
        show_fps=True,
        enable_speed_control=True,
    )
    player = AsciiPlayer("video.mp4", config=config)
    player.play()

Controls:
    Space       - Play/Pause toggle
    Q / Escape  - Stop and exit
    Left/Right  - Seek (arrow keys enter interactive cursor mode)
    Enter       - Confirm seek position
    Home/End    - Jump to start/end
    +/-         - Speed control (±0.25x)
    M           - Cycle through render modes
"""

from __future__ import annotations

import os
import signal
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from blessed import Terminal

from .renderer import AsciiRenderer, RenderMode
from ..stream_view import VideoStream

if TYPE_CHECKING:
    from imagestag.image import Image

# ANSI escape codes
ESC = "\033"
CLEAR_SCREEN = f"{ESC}[2J"
CURSOR_HOME = f"{ESC}[H"
HIDE_CURSOR = f"{ESC}[?25l"
SHOW_CURSOR = f"{ESC}[?25h"
RESET = f"{ESC}[0m"

# Box drawing characters for frame
BOX_TL = "╔"
BOX_TR = "╗"
BOX_BL = "╚"
BOX_BR = "╝"
BOX_H = "═"
BOX_V = "║"


class PlaybackState(Enum):
    """Playback state machine."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    SEEKING = "seeking"


@dataclass
class AsciiPlayerConfig:
    """Configuration for AsciiPlayer UI and controls."""

    # UI elements visibility
    show_progress_bar: bool = True
    show_time: bool = True
    show_mode: bool = True
    show_speed: bool = True
    show_fps: bool = True
    show_frame: bool = True  # Decorative frame around video

    # Control enablement
    enable_seek: bool = True
    enable_speed_control: bool = True
    enable_mode_switch: bool = True

    # Speed options
    speed_options: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0)
    default_speed: float = 1.0

    # Seek step size (in seconds)
    seek_step: float = 5.0
    cursor_step_percent: float = 0.01  # 1% of duration per arrow key in cursor mode

    # Video scale (0.0-1.0) - fraction of terminal to use for video
    # 1.0 = full terminal (Doom style), 0.67 = 2/3 of terminal
    video_scale: float = 1.0


class KeyboardHandler:
    """Handle keyboard input using blessed library."""

    def __init__(self, terminal: Terminal):
        self.terminal = terminal
        self._bindings: dict[str, Callable[[], None]] = {}
        self._char_bindings: dict[str, Callable[[], None]] = {}

    def bind(self, key: str, handler: Callable[[], None]) -> None:
        """Bind a handler to a key.

        Key can be a key name (e.g., 'KEY_LEFT', 'KEY_ESCAPE') or a character.
        """
        if key.startswith("KEY_"):
            self._bindings[key] = handler
        else:
            self._char_bindings[key] = handler

    def unbind(self, key: str) -> None:
        """Remove a key binding."""
        if key.startswith("KEY_"):
            self._bindings.pop(key, None)
        else:
            self._char_bindings.pop(key, None)

    def process(self, timeout: float = 0.001) -> bool:
        """Process keyboard input.

        Returns True to continue, False to exit.
        """
        key = self.terminal.inkey(timeout=timeout)
        if key:
            # Check for named keys (arrows, escape, etc.)
            if key.name and key.name in self._bindings:
                self._bindings[key.name]()
                return True

            # Check for character keys
            char = str(key)
            if char in self._char_bindings:
                self._char_bindings[char]()
                return True

        return True


@dataclass
class ProgressBarState:
    """Current state of the progress bar."""

    current_time: float = 0.0
    total_time: float = 0.0
    cursor_position: float | None = None  # None when not in seek mode
    is_seeking: bool = False
    playback_speed: float = 1.0
    render_mode: RenderMode = RenderMode.HALF_BLOCK
    actual_fps: float = 0.0
    playback_state: PlaybackState = PlaybackState.STOPPED


class ProgressBarRenderer:
    """Render the progress bar with seek cursor."""

    # ANSI color scheme
    COLORS = {
        "filled": f"{ESC}[38;2;100;200;100m",  # Green for progress
        "empty": f"{ESC}[38;2;80;80;80m",  # Gray for remaining
        "cursor": f"{ESC}[38;2;255;200;50m",  # Yellow for cursor
        "cursor_bg": f"{ESC}[48;2;60;60;60m",  # Dark bg for cursor mode
        "time": f"{ESC}[38;2;200;200;255m",  # Light blue for time
        "mode": f"{ESC}[38;2;150;150;200m",  # Purple for mode
        "speed": f"{ESC}[38;2;200;180;100m",  # Gold for speed
        "fps": f"{ESC}[38;2;100;180;200m",  # Cyan for FPS
        "bg": f"{ESC}[48;5;236m",  # Dark gray background
        "reset": RESET,
    }

    # Status icons
    ICONS = {
        PlaybackState.PLAYING: "▶",
        PlaybackState.PAUSED: "⏸",
        PlaybackState.STOPPED: "⏹",
        PlaybackState.SEEKING: "⏩",
    }

    def __init__(self, terminal_width: int, config: AsciiPlayerConfig):
        self.terminal_width = terminal_width
        self.config = config

    def set_width(self, width: int) -> None:
        """Update terminal width."""
        self.terminal_width = width

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS or HH:MM:SS."""
        if seconds < 0:
            seconds = 0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def render(self, state: ProgressBarState) -> str:
        """Render the progress bar line."""
        parts = []
        C = self.COLORS

        # Background
        parts.append(C["bg"])

        # Status icon
        icon = self.ICONS.get(state.playback_state, "?")
        parts.append(f" {icon} ")

        # Time display
        if self.config.show_time:
            current = self._format_time(state.current_time)
            total = self._format_time(state.total_time)
            parts.append(f"{C['time']}{current}")

        # Calculate available width for progress bar
        # Reserved: icon(3) + time(12) + total_time(10) + speed(6) + mode(12) + fps(8) + help(10) + padding(8)
        reserved = 3  # Icon
        if self.config.show_time:
            reserved += 12  # Current time
        if self.config.show_time:
            reserved += 10  # Total time
        if self.config.show_speed:
            reserved += 8  # Speed
        if self.config.show_mode:
            reserved += 14  # Mode
        if self.config.show_fps:
            reserved += 10  # FPS
        reserved += 12  # Help hint [h=help]
        reserved += 4  # Padding/separators

        bar_width = max(10, self.terminal_width - reserved)

        # Progress bar
        if self.config.show_progress_bar and state.total_time > 0:
            progress = state.current_time / state.total_time
            progress = max(0.0, min(1.0, progress))
            filled_width = int(progress * bar_width)

            parts.append(" ")

            if state.is_seeking and state.cursor_position is not None:
                # Seeking mode - show cursor position
                cursor_pos = int(state.cursor_position * bar_width)
                parts.append(C["cursor_bg"])

                for i in range(bar_width):
                    if i == cursor_pos:
                        parts.append(f"{C['cursor']}●")
                    elif i < filled_width:
                        parts.append(f"{C['filled']}━")
                    else:
                        parts.append(f"{C['empty']}━")
            else:
                # Normal mode - just show progress
                for i in range(bar_width):
                    if i == filled_width and i > 0:
                        parts.append(f"{C['cursor']}●")
                    elif i < filled_width:
                        parts.append(f"{C['filled']}━")
                    else:
                        parts.append(f"{C['empty']}━")

            parts.append(f"{C['bg']} ")

        # Total time
        if self.config.show_time:
            total = self._format_time(state.total_time)
            parts.append(f"{C['time']}{total}")

        # Speed indicator
        if self.config.show_speed:
            speed_str = f"{state.playback_speed:.2f}x".rstrip("0").rstrip(".")
            if not speed_str.endswith("x"):
                speed_str += "x"
            parts.append(f"  {C['speed']}{speed_str}")

        # Render mode
        if self.config.show_mode:
            mode_name = state.render_mode.value.upper()
            parts.append(f"  {C['mode']}{mode_name}")

        # FPS counter
        if self.config.show_fps:
            parts.append(f"  {C['fps']}{state.actual_fps:4.1f}fps")

        # Help hint
        parts.append(f"  {C['empty']}[h=help]")

        parts.append(" ")
        parts.append(C["reset"])

        # Pad to terminal width
        result = "".join(parts)
        # Note: ANSI codes don't count towards visible width
        # We'd need to strip ANSI to calculate true visible width
        return result


class PlaybackController:
    """Control video playback with speed adjustment and seeking."""

    def __init__(
        self,
        video: VideoStream,
        config: AsciiPlayerConfig,
    ):
        self.video = video
        self.config = config
        self._state = PlaybackState.STOPPED
        self._speed = config.default_speed
        self._pause_position: float = 0.0

    @property
    def state(self) -> PlaybackState:
        """Current playback state."""
        return self._state

    @property
    def speed(self) -> float:
        """Current playback speed multiplier."""
        return self._speed

    @property
    def current_time(self) -> float:
        """Current playback position in seconds."""
        if self._state == PlaybackState.STOPPED:
            return 0.0
        if self._state == PlaybackState.PAUSED:
            return self._pause_position
        # Use VideoStream's current position
        return self.video.current_position

    @property
    def duration(self) -> float:
        """Total video duration in seconds."""
        return self.video.duration

    def play(self) -> None:
        """Start or resume playback."""
        if self._state == PlaybackState.STOPPED:
            self.video.start()
        elif self._state == PlaybackState.PAUSED:
            self.video.resume()
        self._state = PlaybackState.PLAYING

    def pause(self) -> None:
        """Pause playback."""
        if self._state == PlaybackState.PLAYING:
            self._pause_position = self.video.current_position
            self.video.pause()
            self._state = PlaybackState.PAUSED

    def toggle(self) -> None:
        """Toggle between play and pause."""
        if self._state == PlaybackState.PLAYING:
            self.pause()
        elif self._state in (PlaybackState.PAUSED, PlaybackState.STOPPED):
            self.play()

    def stop(self) -> None:
        """Stop playback completely."""
        self.video.stop()
        self._state = PlaybackState.STOPPED

    def seek_to(self, position: float) -> None:
        """Seek to absolute position in seconds."""
        position = max(0.0, min(position, self.duration))
        # Actually seek the video!
        self.video.seek_to(position)
        if self._state == PlaybackState.PAUSED:
            self._pause_position = position

    def seek_relative(self, delta: float) -> None:
        """Seek relative to current position."""
        new_pos = self.current_time + delta
        self.seek_to(new_pos)

    def set_speed(self, multiplier: float) -> None:
        """Set playback speed."""
        self._speed = max(0.1, min(8.0, multiplier))
        # Note: Speed control would require VideoStream support
        # For now, just track the value for display

    def adjust_speed(self, delta: float) -> None:
        """Adjust speed by delta, snapping to nearest config option."""
        current = self._speed
        options = sorted(self.config.speed_options)

        if delta > 0:
            # Find next higher option
            for opt in options:
                if opt > current + 0.01:
                    self.set_speed(opt)
                    return
            # Already at max
        else:
            # Find next lower option
            for opt in reversed(options):
                if opt < current - 0.01:
                    self.set_speed(opt)
                    return
            # Already at min


class HelpOverlay:
    """Render a help overlay showing keyboard controls."""

    HELP_TEXT = """
╔══════════════════════════════════════════════════════╗
║              ASCII Video Player - Help               ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  PLAYBACK CONTROLS                                   ║
║  ─────────────────                                   ║
║  Space        Play / Pause                           ║
║  Q / Escape   Stop and exit                          ║
║                                                      ║
║  SEEKING                                             ║
║  ───────                                             ║
║  ← / →        Move seek cursor (enter seek mode)     ║
║  Enter        Confirm seek position                  ║
║  Escape       Cancel seek, restore position          ║
║  Home         Jump to start                          ║
║  End          Jump to end                            ║
║                                                      ║
║  SPEED CONTROL                                       ║
║  ─────────────                                       ║
║  + / =        Speed up (0.25x increments)            ║
║  - / _        Speed down (0.25x increments)          ║
║                                                      ║
║  DISPLAY                                             ║
║  ───────                                             ║
║  M            Cycle render mode                      ║
║  H / ?        Toggle this help screen                ║
║                                                      ║
║           Press any key to close help                ║
╚══════════════════════════════════════════════════════╝
"""

    @classmethod
    def render(cls, term_w: int, term_h: int) -> str:
        """Render the help overlay centered on screen."""
        lines = cls.HELP_TEXT.strip().split("\n")
        box_height = len(lines)
        box_width = max(len(line) for line in lines)

        # Center vertically and horizontally
        start_y = max(1, (term_h - box_height) // 2)
        start_x = max(1, (term_w - box_width) // 2)

        output = []
        # Semi-transparent background effect (dim the background)
        output.append(f"{ESC}[48;2;20;20;40m")  # Dark blue background

        for i, line in enumerate(lines):
            # Pad line to box width
            padded = line.ljust(box_width)
            output.append(f"{ESC}[{start_y + i};{start_x}H{ESC}[38;2;200;200;255m{padded}")

        output.append(RESET)
        return "".join(output)


class AsciiPlayer:
    """
    Reusable terminal-based ASCII video player with full keyboard controls.

    Features:
        - Multiple rendering modes (block, half_block, ascii, braille)
        - Interactive seek with cursor scrubbing
        - Speed control
        - Dynamic terminal resize handling
        - Configurable UI elements
    """

    def __init__(
        self,
        video_path: str | Path,
        *,
        mode: RenderMode = RenderMode.HALF_BLOCK,
        config: AsciiPlayerConfig | None = None,
        char_aspect: float = 0.45,
        target_fps: float | None = None,
        loop: bool = True,
    ):
        """
        Initialize the ASCII video player.

        :param video_path: Path to video file
        :param mode: Initial rendering mode
        :param config: Player configuration (uses defaults if None)
        :param char_aspect: Terminal character aspect ratio (width/height)
        :param target_fps: Target FPS (None = video's native FPS, max 30)
        :param loop: Whether to loop the video
        """
        self.video_path = Path(video_path)
        self.mode = mode
        self.config = config or AsciiPlayerConfig()
        self.char_aspect = char_aspect
        self.target_fps = target_fps
        self.loop = loop

        # Will be initialized in play()
        self._terminal: Terminal | None = None
        self._video: VideoStream | None = None
        self._controller: PlaybackController | None = None
        self._keyboard: KeyboardHandler | None = None
        self._progress_bar: ProgressBarRenderer | None = None
        self._renderer: AsciiRenderer | None = None

        # State
        self._running = False
        self._terminal_resized = False
        self._seek_mode = False
        self._seek_cursor: float | None = None
        self._seek_original_position: float = 0.0
        self._show_help = False  # Help overlay toggle

        # FPS tracking
        self._fps_counter: list[float] = []

        # Terminal dimensions cache
        self._last_term_w = 0
        self._last_term_h = 0
        self._video_aspect: float | None = None
        self._progress_bar_y = 0
        self._cached_frame_x = 0
        self._cached_frame_y = 0

    def _setup_keyboard_bindings(self) -> None:
        """Set up keyboard bindings."""
        kb = self._keyboard
        if not kb:
            return

        # Play/Pause
        kb.bind(" ", self._on_toggle)

        # Stop/Exit
        kb.bind("q", self._on_stop)
        kb.bind("Q", self._on_stop)
        kb.bind("KEY_ESCAPE", self._on_stop)

        # Seeking
        if self.config.enable_seek:
            kb.bind("KEY_LEFT", self._on_left)
            kb.bind("KEY_RIGHT", self._on_right)
            kb.bind("KEY_HOME", self._on_home)
            kb.bind("KEY_END", self._on_end)
            kb.bind("KEY_ENTER", self._on_enter)

        # Speed control
        if self.config.enable_speed_control:
            kb.bind("+", self._on_speed_up)
            kb.bind("=", self._on_speed_up)  # Same key without shift
            kb.bind("-", self._on_speed_down)
            kb.bind("_", self._on_speed_down)

        # Mode switching
        if self.config.enable_mode_switch:
            kb.bind("m", self._on_mode_switch)
            kb.bind("M", self._on_mode_switch)

        # Help toggle
        kb.bind("h", self._on_help_toggle)
        kb.bind("H", self._on_help_toggle)
        kb.bind("?", self._on_help_toggle)

    def _on_help_toggle(self) -> None:
        """Toggle help overlay."""
        self._show_help = not self._show_help
        if self._show_help:
            # Force redraw
            self._terminal_resized = True

    def _on_any_key_dismiss_help(self) -> None:
        """Dismiss help on any key press."""
        if self._show_help:
            self._show_help = False
            self._terminal_resized = True

    def _on_toggle(self) -> None:
        """Handle play/pause toggle."""
        if self._controller:
            if self._seek_mode:
                # In seek mode, space confirms seek
                self._confirm_seek()
            else:
                self._controller.toggle()

    def _on_stop(self) -> None:
        """Handle stop/exit."""
        if self._seek_mode:
            self._cancel_seek()
        else:
            self._running = False

    def _on_left(self) -> None:
        """Handle left arrow."""
        if not self._controller:
            return

        if self._seek_mode:
            # Move cursor left
            if self._seek_cursor is not None:
                self._seek_cursor = max(
                    0.0,
                    self._seek_cursor - self.config.cursor_step_percent
                )
        else:
            # Enter seek mode or seek directly
            self._enter_seek_mode()
            if self._seek_cursor is not None:
                self._seek_cursor = max(
                    0.0,
                    self._seek_cursor - self.config.cursor_step_percent
                )

    def _on_right(self) -> None:
        """Handle right arrow."""
        if not self._controller:
            return

        if self._seek_mode:
            # Move cursor right
            if self._seek_cursor is not None:
                self._seek_cursor = min(
                    1.0,
                    self._seek_cursor + self.config.cursor_step_percent
                )
        else:
            # Enter seek mode
            self._enter_seek_mode()
            if self._seek_cursor is not None:
                self._seek_cursor = min(
                    1.0,
                    self._seek_cursor + self.config.cursor_step_percent
                )

    def _on_home(self) -> None:
        """Jump to start."""
        if self._controller:
            if self._seek_mode:
                self._seek_cursor = 0.0
            else:
                self._controller.seek_to(0.0)

    def _on_end(self) -> None:
        """Jump to end."""
        if self._controller:
            if self._seek_mode:
                self._seek_cursor = 1.0
            else:
                self._controller.seek_to(self._controller.duration - 0.1)

    def _on_enter(self) -> None:
        """Confirm seek in seek mode."""
        if self._seek_mode:
            self._confirm_seek()

    def _on_speed_up(self) -> None:
        """Increase playback speed."""
        if self._controller:
            self._controller.adjust_speed(0.25)

    def _on_speed_down(self) -> None:
        """Decrease playback speed."""
        if self._controller:
            self._controller.adjust_speed(-0.25)

    def _on_mode_switch(self) -> None:
        """Cycle through render modes."""
        modes = list(RenderMode)
        current_idx = modes.index(self.mode)
        self.mode = modes[(current_idx + 1) % len(modes)]
        # Recreate renderer with new mode
        self._renderer = None

    def _enter_seek_mode(self) -> None:
        """Enter interactive seek mode."""
        if not self._controller:
            return
        self._seek_mode = True
        self._seek_original_position = self._controller.current_time
        duration = self._controller.duration
        if duration > 0:
            self._seek_cursor = self._controller.current_time / duration
        else:
            self._seek_cursor = 0.0

    def _confirm_seek(self) -> None:
        """Confirm seek and exit seek mode."""
        if not self._controller or self._seek_cursor is None:
            return
        target_time = self._seek_cursor * self._controller.duration
        self._controller.seek_to(target_time)
        self._seek_mode = False
        self._seek_cursor = None

    def _cancel_seek(self) -> None:
        """Cancel seek and restore original position."""
        if self._controller:
            self._controller.seek_to(self._seek_original_position)
        self._seek_mode = False
        self._seek_cursor = None

    def _handle_resize(self, signum, frame) -> None:
        """Handle terminal resize signal."""
        self._terminal_resized = True

    def _get_terminal_size(self) -> tuple[int, int]:
        """Get terminal size with fallback."""
        try:
            size = os.get_terminal_size()
            return size.columns, size.lines
        except OSError:
            return 80, 24

    def _calculate_video_dimensions(
        self, term_w: int, term_h: int
    ) -> tuple[int, int, int, int, int, int, int]:
        """
        Calculate video dimensions based on config.video_scale.

        Returns (video_w, video_h, frame_x, frame_y, frame_w, frame_h, progress_bar_y)
        """
        if self._video_aspect is None:
            return 40, 20, 10, 5, 42, 22, 28

        scale = self.config.video_scale

        # Calculate max frame dimensions based on scale
        # Leave 1 row for progress bar below the frame
        max_frame_w = int(term_w * scale)
        max_frame_h = int((term_h - 1) * scale)  # -1 for progress bar

        # Account for frame borders (2 chars each side)
        border_size = 2 if self.config.show_frame else 0
        max_video_w = max_frame_w - border_size
        max_video_h = max_frame_h - border_size

        # Calculate video size maintaining aspect ratio
        adjusted_aspect = self._video_aspect * self.char_aspect

        video_w = max_video_w
        video_h = int(video_w * adjusted_aspect)

        if video_h > max_video_h:
            video_h = max_video_h
            video_w = int(video_h / adjusted_aspect)

        video_w = max(20, video_w)
        video_h = max(10, video_h)

        frame_w = video_w + border_size
        frame_h = video_h + border_size

        # Center the frame horizontally, position at top
        frame_x = (term_w - frame_w) // 2
        frame_y = 1  # Start at top

        # Progress bar goes directly below the frame
        progress_bar_y = frame_y + frame_h

        return video_w, video_h, frame_x, frame_y, frame_w, frame_h, progress_bar_y

    def _draw_frame(
        self, frame_x: int, frame_y: int, frame_w: int, frame_h: int, title: str = ""
    ) -> str:
        """Draw a decorative frame around the video area."""
        if not self.config.show_frame:
            return ""

        output = []
        frame_color = f"{ESC}[38;2;100;150;200m"
        title_color = f"{ESC}[38;2;200;200;255m{ESC}[1m"

        # Top border with title
        top_line = BOX_TL + BOX_H * (frame_w - 2) + BOX_TR
        if title:
            title_display = f" {title} "
            title_start = (frame_w - len(title_display)) // 2
            if title_start > 1:
                top_line = (
                    BOX_TL
                    + BOX_H * (title_start - 1)
                    + title_color
                    + title_display
                    + frame_color
                    + BOX_H * (frame_w - title_start - len(title_display) - 1)
                    + BOX_TR
                )

        output.append(f"{ESC}[{frame_y};{frame_x + 1}H{frame_color}{top_line}{RESET}")

        # Side borders
        for row in range(1, frame_h - 1):
            output.append(f"{ESC}[{frame_y + row};{frame_x + 1}H{frame_color}{BOX_V}")
            output.append(f"{ESC}[{frame_y + row};{frame_x + frame_w}H{BOX_V}{RESET}")

        # Bottom border
        bottom_line = BOX_BL + BOX_H * (frame_w - 2) + BOX_BR
        output.append(
            f"{ESC}[{frame_y + frame_h - 1};{frame_x + 1}H{frame_color}{bottom_line}{RESET}"
        )

        return "".join(output)

    def _update_fps(self) -> float:
        """Update FPS counter and return current FPS."""
        now = time.time()
        self._fps_counter.append(now)
        # Keep last second
        self._fps_counter = [t for t in self._fps_counter if now - t < 1.0]
        return float(len(self._fps_counter))

    def play(self) -> None:
        """Start video playback with interactive controls."""
        if not self.video_path.exists():
            print(f"Video not found: {self.video_path}")
            print("Run: python scripts/download_test_media.py")
            return

        # Initialize components
        self._terminal = Terminal()
        self._video = VideoStream(str(self.video_path), loop=self.loop)
        self._controller = PlaybackController(self._video, self.config)
        self._keyboard = KeyboardHandler(self._terminal)
        self._setup_keyboard_bindings()

        # Determine effective FPS
        if self.target_fps is None:
            effective_fps = min(self._video.fps, 30.0)
        else:
            effective_fps = min(self.target_fps, 30.0)
        frame_interval = 1.0 / effective_fps

        # Get video title
        video_title = self.video_path.stem.replace("_", " ").title()

        # Setup terminal resize handler (Unix only)
        if hasattr(signal, "SIGWINCH"):
            signal.signal(signal.SIGWINCH, self._handle_resize)

        self._running = True

        # Enter terminal fullscreen mode
        with self._terminal.fullscreen(), self._terminal.cbreak(), self._terminal.hidden_cursor():
            # Start playback
            self._controller.play()

            try:
                while self._running:
                    loop_start = time.time()

                    # Process keyboard input (1ms timeout for responsiveness)
                    if self._show_help:
                        # When help is showing, any key dismisses it
                        key = self._terminal.inkey(timeout=0.001)
                        if key:
                            self._show_help = False
                            self._terminal_resized = True  # Force redraw
                    else:
                        self._keyboard.process(timeout=0.001)

                    if not self._running:
                        break

                    # Get current frame
                    current_time = self._controller.current_time
                    frame, _ = self._video.get_frame(current_time)

                    if frame is None:
                        time.sleep(0.001)
                        continue

                    # Get video aspect from first frame
                    if self._video_aspect is None:
                        self._video_aspect = frame.height / frame.width

                    # Check for terminal resize
                    term_w, term_h = self._get_terminal_size()
                    if (
                        term_w != self._last_term_w
                        or term_h != self._last_term_h
                        or self._terminal_resized
                        or self._renderer is None
                    ):
                        self._terminal_resized = False
                        self._last_term_w, self._last_term_h = term_w, term_h

                        # Calculate dimensions
                        (
                            video_w,
                            video_h,
                            frame_x,
                            frame_y,
                            frame_w,
                            frame_h,
                            progress_bar_y,
                        ) = self._calculate_video_dimensions(term_w, term_h)
                        self._progress_bar_y = progress_bar_y
                        self._cached_frame_x = frame_x
                        self._cached_frame_y = frame_y

                        # Create/recreate renderer
                        self._renderer = AsciiRenderer(
                            width=video_w,
                            max_height=video_h,
                            mode=self.mode,
                            char_aspect=self.char_aspect,
                            margin_x=0,
                            margin_y=0,
                        )

                        # Create progress bar renderer
                        self._progress_bar = ProgressBarRenderer(term_w, self.config)

                        # Clear and redraw frame
                        sys.stdout.write(CLEAR_SCREEN)
                        sys.stdout.write(
                            self._draw_frame(
                                frame_x, frame_y, frame_w, frame_h, video_title
                            )
                        )
                        sys.stdout.flush()

                    # Build all output in a single buffer to minimize syscalls
                    output_buffer = []

                    # Render frame
                    if self._renderer:
                        ascii_frame = self._renderer.render(frame)

                        # Use cached dimensions (calculated on resize)
                        border_offset = 1 if self.config.show_frame else 0
                        video_start_x = self._cached_frame_x + 1 + border_offset
                        video_start_y = self._cached_frame_y + border_offset

                        # Output frame lines
                        lines = ascii_frame.split("\n")
                        for i, line in enumerate(lines):
                            output_buffer.append(
                                f"{ESC}[{video_start_y + i};{video_start_x}H{line}"
                            )

                    # Update and render progress bar
                    if self._progress_bar:
                        pb_state = ProgressBarState(
                            current_time=current_time,
                            total_time=self._controller.duration,
                            cursor_position=self._seek_cursor,
                            is_seeking=self._seek_mode,
                            playback_speed=self._controller.speed,
                            render_mode=self.mode,
                            actual_fps=self._update_fps(),
                            playback_state=self._controller.state,
                        )
                        progress_line = self._progress_bar.render(pb_state)
                        output_buffer.append(f"{ESC}[{self._progress_bar_y};0H{progress_line}")

                    # Render help overlay if active
                    if self._show_help:
                        output_buffer.append(
                            HelpOverlay.render(self._last_term_w, self._last_term_h)
                        )

                    # Single write and flush
                    sys.stdout.write("".join(output_buffer))
                    sys.stdout.flush()

                    # Frame rate limiting
                    elapsed = time.time() - loop_start
                    sleep_time = frame_interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            except KeyboardInterrupt:
                pass
            finally:
                self._controller.stop()
                self._running = False

        # Cleanup message
        print(f"\nPlayback stopped")


__all__ = [
    "AsciiPlayer",
    "AsciiPlayerConfig",
    "AsciiRenderer",
    "HelpOverlay",
    "KeyboardHandler",
    "PlaybackController",
    "PlaybackState",
    "ProgressBarRenderer",
    "ProgressBarState",
    "RenderMode",
]
