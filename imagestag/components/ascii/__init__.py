"""ASCII rendering and playback components.

This module provides terminal-based ASCII art rendering and video playback:
- AsciiRenderer: Convert images to colored ASCII/Unicode art
- TerminalPlayer: Interactive terminal video player with keyboard controls
"""

from .renderer import AsciiRenderer, RenderMode, render_frame_to_terminal
from .terminal_player import (
    TerminalPlayer,
    TerminalPlayerConfig,
    TerminalMultiPlayer,
    PlayerSlot,
    HelpOverlay,
    KeyboardHandler,
    PlaybackController,
    PlaybackState,
    ProgressBarRenderer,
    ProgressBarState,
)

# Backwards compatibility aliases
AsciiPlayer = TerminalPlayer
AsciiPlayerConfig = TerminalPlayerConfig

__all__ = [
    # Renderer
    "AsciiRenderer",
    "RenderMode",
    "render_frame_to_terminal",
    # Single Player
    "TerminalPlayer",
    "TerminalPlayerConfig",
    "AsciiPlayer",  # Alias for backwards compatibility
    "AsciiPlayerConfig",  # Alias for backwards compatibility
    # Multi-Player
    "TerminalMultiPlayer",
    "PlayerSlot",
    # Internals (for advanced use)
    "HelpOverlay",
    "KeyboardHandler",
    "PlaybackController",
    "PlaybackState",
    "ProgressBarRenderer",
    "ProgressBarState",
]
