"""
Terminal Video Player - Interactive terminal-based video player.

A reusable component for playing videos as colored ASCII art in the terminal
with full keyboard controls for play/pause, seeking, speed control, and more.

Example:
    from imagestag.components.ascii import TerminalPlayer, TerminalPlayerConfig

    # Simple usage
    player = TerminalPlayer("video.mp4")
    player.play()

    # With custom configuration
    config = TerminalPlayerConfig(
        show_progress_bar=True,
        show_fps=True,
        enable_speed_control=True,
    )
    player = TerminalPlayer("video.mp4", config=config)
    player.play()

Controls:
    Space       - Play/Pause toggle
    Q / Escape  - Stop and exit
    Left/Right  - Seek (arrow keys enter interactive cursor mode)
    Enter       - Confirm seek position
    Home/End    - Jump to start/end
    +/-         - Speed control (±0.25x)
    M           - Cycle through render modes
    H / ?       - Show help
"""

from __future__ import annotations

import os
import signal
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

from blessed import Terminal

from .renderer import AsciiRenderer, RenderMode
from ...streams import ImageStream, VideoStream

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
class TerminalPlayerConfig:
    """Configuration for TerminalPlayer UI and controls."""

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
    enable_mouse: bool = False  # Mouse support (experimental, terminal-dependent)

    # Speed options
    speed_options: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0, 8.0, 16.0)
    default_speed: float = 1.0

    # Seek step size (in seconds)
    seek_step: float = 5.0
    cursor_step_percent: float = 0.01  # 1% of duration per arrow key in cursor mode

    # Video scale (0.0-1.0) - fraction of terminal to use for video
    # 1.0 = full terminal (Doom style), 0.67 = 2/3 of terminal
    video_scale: float = 1.0


class KeyboardHandler:
    """Handle keyboard and mouse input using blessed library."""

    def __init__(self, terminal: Terminal):
        self.terminal = terminal
        self._bindings: dict[str, Callable[[], None]] = {}
        self._char_bindings: dict[str, Callable[[], None]] = {}
        self._mouse_click_handler: Callable[[int, int], None] | None = None
        self._mouse_scroll_up_handler: Callable[[], None] | None = None
        self._mouse_scroll_down_handler: Callable[[], None] | None = None

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

    def bind_mouse_click(self, handler: Callable[[int, int], None]) -> None:
        """Bind a handler for mouse clicks. Handler receives (x, y) coordinates."""
        self._mouse_click_handler = handler

    def bind_mouse_scroll(
        self,
        up_handler: Callable[[], None] | None = None,
        down_handler: Callable[[], None] | None = None,
    ) -> None:
        """Bind handlers for mouse scroll wheel."""
        self._mouse_scroll_up_handler = up_handler
        self._mouse_scroll_down_handler = down_handler

    def process(self, timeout: float = 0.001) -> bool:
        """Process keyboard and mouse input.

        Returns True to continue, False to exit.
        """
        key = self.terminal.inkey(timeout=timeout)
        if key:
            # Check for mouse events (blessed provides these via special sequences)
            if hasattr(key, 'is_sequence') and key.is_sequence:
                # Mouse scroll wheel events
                if key.name == 'KEY_SUP' or key.code == 337:  # Scroll up
                    if self._mouse_scroll_up_handler:
                        self._mouse_scroll_up_handler()
                    return True
                elif key.name == 'KEY_SDOWN' or key.code == 336:  # Scroll down
                    if self._mouse_scroll_down_handler:
                        self._mouse_scroll_down_handler()
                    return True

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

    def process_mouse(self, timeout: float = 0.001) -> tuple[str | None, int, int]:
        """Process input and return mouse event info if any.

        Returns (event_type, x, y) where event_type is 'click', 'scroll_up',
        'scroll_down', or None for keyboard events.
        """
        key = self.terminal.inkey(timeout=timeout)
        if not key:
            return None, 0, 0

        # Check for mouse click events
        # blessed uses special escape sequences for mouse events
        if hasattr(key, 'is_sequence') and key.is_sequence:
            # Mouse scroll wheel
            if key.name == 'KEY_SUP' or key.code == 337:
                return 'scroll_up', 0, 0
            elif key.name == 'KEY_SDOWN' or key.code == 336:
                return 'scroll_down', 0, 0

        # Handle keyboard events through normal bindings
        if key.name and key.name in self._bindings:
            self._bindings[key.name]()
        elif str(key) in self._char_bindings:
            self._char_bindings[str(key)]()

        return None, 0, 0


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

    # Status icons - show the ACTION available (like media players)
    # When playing, show pause button; when paused, show play button
    ICONS = {
        PlaybackState.PLAYING: "⏸",  # Can pause
        PlaybackState.PAUSED: "▶",   # Can play
        PlaybackState.STOPPED: "▶",  # Can play
        PlaybackState.SEEKING: "⏩",
    }

    def __init__(self, terminal_width: int, config: TerminalPlayerConfig):
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
    """Control stream playback with speed adjustment and seeking.

    Works with any ImageStream. Seeking is only available for streams
    that support it (e.g., VideoStream).
    """

    def __init__(
        self,
        stream: ImageStream,
        config: TerminalPlayerConfig,
    ):
        self.stream = stream
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
    def is_seekable(self) -> bool:
        """Whether the stream supports seeking."""
        return hasattr(self.stream, 'seek_to') and hasattr(self.stream, 'duration')

    @property
    def current_time(self) -> float:
        """Current playback position in seconds."""
        if self._state == PlaybackState.STOPPED:
            return 0.0
        if self._state == PlaybackState.PAUSED:
            return self._pause_position
        # Use stream's current position if available, else elapsed_time
        if hasattr(self.stream, 'current_position'):
            return self.stream.current_position
        return self.stream.elapsed_time

    @property
    def duration(self) -> float:
        """Total duration in seconds (0 for infinite streams)."""
        if hasattr(self.stream, 'duration'):
            return self.stream.duration
        return 0.0

    def play(self) -> None:
        """Start or resume playback."""
        if self._state == PlaybackState.STOPPED:
            self.stream.start()
        elif self._state == PlaybackState.PAUSED:
            self.stream.resume()
        self._state = PlaybackState.PLAYING

    def pause(self) -> None:
        """Pause playback."""
        if self._state == PlaybackState.PLAYING:
            self._pause_position = self.current_time
            self.stream.pause()
            self._state = PlaybackState.PAUSED

    def toggle(self) -> None:
        """Toggle between play and pause."""
        if self._state == PlaybackState.PLAYING:
            self.pause()
        elif self._state in (PlaybackState.PAUSED, PlaybackState.STOPPED):
            self.play()

    def stop(self) -> None:
        """Stop playback completely."""
        self.stream.stop()
        self._state = PlaybackState.STOPPED

    def seek_to(self, position: float) -> None:
        """Seek to absolute position in seconds (if supported)."""
        if not self.is_seekable:
            return
        position = max(0.0, min(position, self.duration))
        self.stream.seek_to(position)
        if self._state == PlaybackState.PAUSED:
            self._pause_position = position

    def seek_relative(self, delta: float) -> None:
        """Seek relative to current position."""
        if self.is_seekable:
            new_pos = self.current_time + delta
            self.seek_to(new_pos)

    def set_speed(self, multiplier: float) -> None:
        """Set playback speed."""
        self._speed = max(0.25, min(16.0, multiplier))
        self.stream.playback_speed = self._speed

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


class TerminalPlayer:
    """
    Reusable terminal-based ASCII stream player with full keyboard controls.

    Accepts either a video file path or any ImageStream, making it interchangeable
    with StreamView for terminal-based rendering.

    Features:
        - Multiple rendering modes (block, half_block, ascii, braille)
        - Interactive seek with cursor scrubbing (for seekable streams)
        - Speed control
        - Dynamic terminal resize handling
        - Configurable UI elements
    """

    def __init__(
        self,
        source: str | Path | ImageStream,
        *,
        mode: RenderMode = RenderMode.HALF_BLOCK,
        config: TerminalPlayerConfig | None = None,
        char_aspect: float = 0.45,
        target_fps: float | None = None,
        loop: bool = True,
        title: str | None = None,
    ):
        """
        Initialize the ASCII stream player.

        :param source: Video file path OR any ImageStream
        :param mode: Initial rendering mode
        :param config: Player configuration (uses defaults if None)
        :param char_aspect: Terminal character aspect ratio (width/height)
        :param target_fps: Target FPS (None = stream's native FPS, max 30)
        :param loop: Whether to loop (only applies to video files)
        :param title: Display title (auto-detected for video files)
        """
        # Handle both path and stream inputs
        if isinstance(source, ImageStream):
            self._stream = source
            self.video_path = None
            self._title = title or "Stream"
        else:
            self._stream = None
            self.video_path = Path(source)
            self._title = title or self.video_path.stem.replace("_", " ").title()

        self.mode = mode
        self.config = config or TerminalPlayerConfig()
        self.char_aspect = char_aspect
        self.target_fps = target_fps
        self.loop = loop

        # Will be initialized in play()
        self._terminal: Terminal | None = None
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
        self._cached_frame_w = 0

    def _setup_keyboard_bindings(self) -> None:
        """Set up keyboard and mouse bindings."""
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

        # Mouse support
        if self.config.enable_mouse:
            kb.bind_mouse_click(self._on_mouse_click)
            if self.config.enable_speed_control:
                kb.bind_mouse_scroll(
                    up_handler=self._on_speed_up,
                    down_handler=self._on_speed_down,
                )

    def _on_mouse_click(self, x: int, y: int) -> None:
        """Handle mouse click - seek if clicking on progress bar."""
        if not self._controller:
            return

        # Check if click is on the progress bar row
        if y == self._progress_bar_y and self.config.enable_seek:
            # Calculate seek position based on x coordinate
            # Progress bar starts after icon (3 chars) and time (12 chars) = 15 chars
            # and ends before end time, speed, mode, fps, help
            term_w = self._last_term_w
            bar_start = 16  # Approximate start of progress bar
            bar_end = term_w - 50  # Approximate end of progress bar

            if bar_start <= x <= bar_end:
                # Calculate position as fraction
                progress = (x - bar_start) / (bar_end - bar_start)
                progress = max(0.0, min(1.0, progress))

                # Seek to position
                target_time = progress * self._controller.duration
                self._controller.seek_to(target_time)
        else:
            # Click anywhere else toggles play/pause
            self._on_toggle()

    def _process_input(self) -> None:
        """Process keyboard and mouse input."""
        if not self._terminal or not self._keyboard:
            return

        timeout = 0.01 if self.config.enable_mouse else 0.001
        key = self._terminal.inkey(timeout=timeout)
        if not key:
            return

        key_str = str(key)

        # Mouse event handling (only if enabled)
        if self.config.enable_mouse:
            # Check for SGR mouse format: \x1b[<btn;x;y[Mm]
            if '\x1b[<' in key_str:
                try:
                    idx = key_str.find('\x1b[<')
                    data = key_str[idx + 3:]
                    if 'M' in data or 'm' in data:
                        end_idx = data.find('M') if 'M' in data else data.find('m')
                        is_press = data[end_idx] == 'M'
                        parts = data[:end_idx].split(';')
                        if len(parts) == 3:
                            btn = int(parts[0])
                            x = int(parts[1])
                            y = int(parts[2])
                            if is_press:
                                if btn == 0:
                                    self._on_mouse_click(x, y)
                                elif btn == 64:
                                    self._on_speed_up()
                                elif btn == 65:
                                    self._on_speed_down()
                except (ValueError, IndexError):
                    pass
                return

            # Ignore escape sequence fragments when mouse is enabled
            if '\x1b' in key_str and len(key_str) < 10:
                return

        # Handle keyboard events
        if key.name and key.name in self._keyboard._bindings:
            self._keyboard._bindings[key.name]()
        elif key_str in self._keyboard._char_bindings:
            self._keyboard._char_bindings[key_str]()

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
        if self._controller and self._controller.is_seekable:
            if self._seek_mode:
                self._seek_cursor = 0.0
            else:
                self._controller.seek_to(0.0)

    def _on_end(self) -> None:
        """Jump to end."""
        if self._controller and self._controller.is_seekable:
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
        """Enter interactive seek mode (only for seekable streams)."""
        if not self._controller or not self._controller.is_seekable:
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

    def _handle_resize(self, _signum, _frame) -> None:
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
        # Leave 1 row for progress bar at the bottom of the terminal
        max_frame_w = int(term_w * scale)
        max_frame_h = int((term_h - 2) * scale)  # -2 for progress bar row

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

        # Progress bar goes at the last row of the terminal (always visible)
        progress_bar_y = term_h

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
        """Start stream playback with interactive controls."""
        # Get or create the stream
        if self._stream is not None:
            stream = self._stream
        else:
            if self.video_path is None or not self.video_path.exists():
                print(f"Video not found: {self.video_path}")
                print("Run: python scripts/download_test_media.py")
                return
            stream = VideoStream(str(self.video_path), loop=self.loop)

        # Initialize components
        self._terminal = Terminal()
        self._controller = PlaybackController(stream, self.config)
        self._keyboard = KeyboardHandler(self._terminal)
        self._setup_keyboard_bindings()

        # Determine effective FPS
        stream_fps = getattr(stream, 'fps', 30.0)
        if self.target_fps is None:
            effective_fps = min(stream_fps, 30.0)
        else:
            effective_fps = min(self.target_fps, 30.0)
        frame_interval = 1.0 / effective_fps

        # Setup terminal resize handler (Unix only)
        if hasattr(signal, "SIGWINCH"):
            signal.signal(signal.SIGWINCH, self._handle_resize)

        self._running = True

        # Enter terminal fullscreen mode with mouse tracking
        with self._terminal.fullscreen(), self._terminal.cbreak(), self._terminal.hidden_cursor():
            # Enable mouse tracking if configured
            if self.config.enable_mouse:
                # Enable SGR mouse mode for better coordinate reporting
                sys.stdout.write(f"{ESC}[?1000h")  # Enable mouse tracking
                sys.stdout.write(f"{ESC}[?1006h")  # Enable SGR extended mode
                sys.stdout.flush()

            # Start playback
            self._controller.play()

            try:
                while self._running:
                    loop_start = time.time()

                    # Process keyboard and mouse input (1ms timeout for responsiveness)
                    if self._show_help:
                        # When help is showing, any key dismisses it
                        key = self._terminal.inkey(timeout=0.001)
                        if key:
                            self._show_help = False
                            self._terminal_resized = True  # Force redraw
                    else:
                        self._process_input()

                    if not self._running:
                        break

                    # Get current frame
                    current_time = self._controller.current_time
                    frame, _ = stream.get_frame(current_time)

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
                        self._cached_frame_w = frame_w

                        # Create/recreate renderer
                        self._renderer = AsciiRenderer(
                            width=video_w,
                            max_height=video_h,
                            mode=self.mode,
                            char_aspect=self.char_aspect,
                            margin_x=0,
                            margin_y=0,
                        )

                        # Create progress bar renderer (same width as frame, centered)
                        self._progress_bar = ProgressBarRenderer(frame_w, self.config)

                        # Clear and redraw frame
                        sys.stdout.write(CLEAR_SCREEN)
                        sys.stdout.write(
                            self._draw_frame(
                                frame_x, frame_y, frame_w, frame_h, self._title
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

                    # Update and render progress bar (centered below frame)
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
                        # Position at frame_x + 1 to align with frame content
                        pb_x = self._cached_frame_x + 1
                        output_buffer.append(f"{ESC}[{self._progress_bar_y};{pb_x}H{progress_line}")

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
                # Disable mouse tracking before exiting
                if self.config.enable_mouse:
                    sys.stdout.write(f"{ESC}[?1006l")  # Disable SGR mode
                    sys.stdout.write(f"{ESC}[?1000l")  # Disable mouse tracking
                    sys.stdout.flush()

                self._controller.stop()
                self._running = False

        # Cleanup message
        print(f"\nPlayback stopped")


# =============================================================================
# Multi-Player Layout Support
# =============================================================================


@dataclass
class PlayerSlot:
    """Configuration for a single player slot in a multi-player layout."""

    video_path: str | Path
    mode: RenderMode = RenderMode.HALF_BLOCK
    label: str = ""  # Optional label shown above the player


class TerminalMultiPlayer:
    """
    Multi-player terminal video player with grid layouts.

    Easily play multiple videos side-by-side in the terminal.

    Example:
        from imagestag.components.ascii import TerminalMultiPlayer

        # Simple 2x2 grid
        multi = TerminalMultiPlayer([
            "video1.mp4",
            "video2.mp4",
            "video3.mp4",
            "video4.mp4",
        ], layout="2x2")
        multi.play()

        # Horizontal split (side by side)
        multi = TerminalMultiPlayer(["left.mp4", "right.mp4"], layout="1x2")
        multi.play()

        # Vertical split (top/bottom)
        multi = TerminalMultiPlayer(["top.mp4", "bottom.mp4"], layout="2x1")
        multi.play()

        # Custom labels
        multi = TerminalMultiPlayer([
            PlayerSlot("cam1.mp4", label="Camera 1"),
            PlayerSlot("cam2.mp4", label="Camera 2"),
        ], layout="1x2")
        multi.play()

    Layouts:
        "1x1" - Single player (default)
        "1x2" - Two players side by side (horizontal split)
        "2x1" - Two players stacked (vertical split)
        "2x2" - Four players in a 2x2 grid
        "3x2" - Six players in a 3 rows x 2 cols grid
        "2x3" - Six players in a 2 rows x 3 cols grid

    Controls (same as single player):
        Space       - Play/Pause all
        Q / Escape  - Stop and exit
        +/-         - Speed control (all players)
        M           - Cycle render modes (all players)
        1-9         - Focus on specific player (if < 10 players)
    """

    LAYOUTS = {
        "1x1": (1, 1),
        "1x2": (1, 2),  # 1 row, 2 cols (side by side)
        "2x1": (2, 1),  # 2 rows, 1 col (stacked)
        "2x2": (2, 2),
        "3x2": (3, 2),  # 3 rows, 2 cols
        "2x3": (2, 3),  # 2 rows, 3 cols
        "3x3": (3, 3),
    }

    def __init__(
        self,
        videos: list[str | Path | PlayerSlot],
        *,
        layout: str = "auto",
        mode: RenderMode = RenderMode.HALF_BLOCK,
        char_aspect: float = 0.45,
        loop: bool = True,
        sync_playback: bool = True,
    ):
        """
        Initialize multi-player.

        :param videos: List of video paths or PlayerSlot configurations
        :param layout: Layout string ("1x2", "2x2", etc.) or "auto" to determine from video count
        :param mode: Default render mode for all players
        :param char_aspect: Terminal character aspect ratio
        :param loop: Whether to loop videos
        :param sync_playback: Keep all players synchronized
        """
        self.slots: list[PlayerSlot] = []
        for v in videos:
            if isinstance(v, PlayerSlot):
                self.slots.append(v)
            else:
                self.slots.append(PlayerSlot(video_path=v, mode=mode))

        self.layout = self._determine_layout(layout, len(self.slots))
        self.char_aspect = char_aspect
        self.loop = loop
        self.sync_playback = sync_playback
        self.default_mode = mode

        # Runtime state
        self._terminal: Terminal | None = None
        self._renderers: list[AsciiRenderer] = []
        self._videos: list[VideoStream] = []
        self._controllers: list[PlaybackController] = []
        self._running = False
        self._focused_player: int | None = None  # None = all, 0-N = specific

    def _determine_layout(self, layout: str, count: int) -> tuple[int, int]:
        """Determine grid layout from string or video count."""
        if layout != "auto":
            if layout in self.LAYOUTS:
                return self.LAYOUTS[layout]
            # Try parsing "RxC" format
            if "x" in layout:
                parts = layout.lower().split("x")
                if len(parts) == 2:
                    try:
                        return (int(parts[0]), int(parts[1]))
                    except ValueError:
                        pass
            raise ValueError(f"Invalid layout: {layout}. Use 'auto' or 'RxC' format (e.g., '2x2')")

        # Auto-determine layout based on count
        if count == 1:
            return (1, 1)
        elif count == 2:
            return (1, 2)  # Side by side
        elif count <= 4:
            return (2, 2)
        elif count <= 6:
            return (2, 3)
        elif count <= 9:
            return (3, 3)
        else:
            # For larger counts, try to make it roughly square
            import math
            cols = math.ceil(math.sqrt(count))
            rows = math.ceil(count / cols)
            return (rows, cols)

    def play(self) -> None:
        """Start multi-player playback."""
        if not self.slots:
            print("No videos to play")
            return

        # Validate all video paths
        for slot in self.slots:
            path = Path(slot.video_path)
            if not path.exists():
                print(f"Video not found: {path}")
                return

        self._terminal = Terminal()
        rows, cols = self.layout

        # Initialize videos and controllers
        config = TerminalPlayerConfig()
        for slot in self.slots:
            video = VideoStream(str(slot.video_path), loop=self.loop)
            self._videos.append(video)
            self._controllers.append(PlaybackController(video, config))

        # Setup keyboard handler
        keyboard = KeyboardHandler(self._terminal)
        self._setup_multi_bindings(keyboard)

        self._running = True

        with self._terminal.fullscreen(), self._terminal.cbreak(), self._terminal.hidden_cursor():
            # Start all videos
            for controller in self._controllers:
                controller.play()

            try:
                while self._running:
                    loop_start = time.time()

                    # Process input
                    keyboard.process(timeout=0.001)
                    if not self._running:
                        break

                    # Get terminal size and calculate cell dimensions
                    term_w, term_h = self._get_terminal_size()
                    cell_w = term_w // cols
                    cell_h = (term_h - 1) // rows  # -1 for status line

                    # Render each player
                    output_buffer = []
                    for i, (slot, video, controller) in enumerate(
                        zip(self.slots, self._videos, self._controllers)
                    ):
                        if i >= rows * cols:
                            break  # Skip if more videos than grid slots

                        row = i // cols
                        col = i % cols
                        x = col * cell_w
                        y = row * cell_h

                        # Get frame
                        frame, _ = video.get_frame(controller.current_time)
                        if frame is None:
                            continue

                        # Create/update renderer for this cell
                        while len(self._renderers) <= i:
                            self._renderers.append(None)

                        if self._renderers[i] is None or self._renderers[i].width != cell_w - 2:
                            self._renderers[i] = AsciiRenderer(
                                width=cell_w - 2,  # -2 for borders
                                max_height=cell_h - 2,  # -2 for label + border
                                mode=slot.mode,
                                char_aspect=self.char_aspect,
                            )

                        # Render frame
                        ascii_frame = self._renderers[i].render(frame)
                        lines = ascii_frame.split("\n")

                        # Draw label if present
                        label_y = y + 1
                        if slot.label:
                            # Truncate/pad label to fit
                            label = slot.label[:cell_w - 2].center(cell_w - 2)
                            highlight = f"{ESC}[1;36m" if self._focused_player == i else f"{ESC}[90m"
                            output_buffer.append(
                                f"{ESC}[{label_y};{x + 2}H{highlight}{label}{RESET}"
                            )
                            label_y += 1

                        # Draw frame content
                        for j, line in enumerate(lines):
                            output_buffer.append(
                                f"{ESC}[{label_y + j};{x + 2}H{line}"
                            )

                    # Draw status line at bottom
                    status = self._render_status_line(term_w)
                    output_buffer.append(f"{ESC}[{term_h};1H{status}")

                    # Output everything
                    sys.stdout.write("".join(output_buffer))
                    sys.stdout.flush()

                    # Frame limiting (~30fps for multi-player)
                    elapsed = time.time() - loop_start
                    sleep_time = (1.0 / 30.0) - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            except KeyboardInterrupt:
                pass
            finally:
                for controller in self._controllers:
                    controller.stop()
                self._running = False

        print("\nMulti-player stopped")

    def _get_terminal_size(self) -> tuple[int, int]:
        """Get terminal size."""
        try:
            size = os.get_terminal_size()
            return size.columns, size.lines
        except OSError:
            return 80, 24

    def _setup_multi_bindings(self, kb: KeyboardHandler) -> None:
        """Setup keyboard bindings for multi-player."""
        kb.bind(" ", self._toggle_all)
        kb.bind("q", self._stop)
        kb.bind("Q", self._stop)
        kb.bind("KEY_ESCAPE", self._stop)
        kb.bind("+", self._speed_up)
        kb.bind("=", self._speed_up)
        kb.bind("-", self._speed_down)
        kb.bind("_", self._speed_down)
        kb.bind("m", self._cycle_mode)
        kb.bind("M", self._cycle_mode)

        # Number keys to focus specific player
        for n in range(1, 10):
            kb.bind(str(n), lambda n=n: self._focus_player(n - 1))
        kb.bind("0", lambda: self._focus_player(None))  # 0 = all

    def _toggle_all(self) -> None:
        """Toggle play/pause for all (or focused) players."""
        targets = [self._focused_player] if self._focused_player is not None else range(len(self._controllers))
        for i in targets:
            if i < len(self._controllers):
                self._controllers[i].toggle()

    def _stop(self) -> None:
        """Stop playback."""
        self._running = False

    def _speed_up(self) -> None:
        """Increase speed."""
        targets = [self._focused_player] if self._focused_player is not None else range(len(self._controllers))
        for i in targets:
            if i < len(self._controllers):
                self._controllers[i].adjust_speed(0.25)

    def _speed_down(self) -> None:
        """Decrease speed."""
        targets = [self._focused_player] if self._focused_player is not None else range(len(self._controllers))
        for i in targets:
            if i < len(self._controllers):
                self._controllers[i].adjust_speed(-0.25)

    def _cycle_mode(self) -> None:
        """Cycle render mode for all (or focused) players."""
        modes = list(RenderMode)
        targets = [self._focused_player] if self._focused_player is not None else range(len(self.slots))
        for i in targets:
            if i < len(self.slots):
                current_idx = modes.index(self.slots[i].mode)
                self.slots[i].mode = modes[(current_idx + 1) % len(modes)]
                if i < len(self._renderers):
                    self._renderers[i] = None  # Force recreation

    def _focus_player(self, index: int | None) -> None:
        """Focus on a specific player or all."""
        if index is None or index < len(self._controllers):
            self._focused_player = index

    def _render_status_line(self, width: int) -> str:
        """Render the status line at the bottom."""
        C = ProgressBarRenderer.COLORS

        # Get state from first controller (or focused)
        idx = self._focused_player if self._focused_player is not None else 0
        if idx < len(self._controllers):
            controller = self._controllers[idx]
            state = controller.state
            speed = controller.speed
            current = controller.current_time
            total = controller.duration
        else:
            state = PlaybackState.STOPPED
            speed = 1.0
            current = 0
            total = 0

        icon = ProgressBarRenderer.ICONS.get(state, "?")
        time_str = f"{int(current // 60):02d}:{int(current % 60):02d}/{int(total // 60):02d}:{int(total % 60):02d}"
        speed_str = f"{speed:.2g}x"
        focus_str = f"[{self._focused_player + 1}]" if self._focused_player is not None else "[All]"
        layout_str = f"{self.layout[0]}x{self.layout[1]}"

        status = f"{C['bg']} {icon} {C['time']}{time_str}  {C['speed']}{speed_str}  {C['mode']}{layout_str}  {focus_str}  {C['empty']}[0=All 1-9=Focus q=Quit]{RESET}"
        return status


__all__ = [
    "TerminalPlayer",
    "TerminalPlayerConfig",
    "TerminalMultiPlayer",
    "PlayerSlot",
    "AsciiRenderer",
    "HelpOverlay",
    "KeyboardHandler",
    "PlaybackController",
    "PlaybackState",
    "ProgressBarRenderer",
    "ProgressBarState",
    "RenderMode",
]
