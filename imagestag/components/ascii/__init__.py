"""ASCII rendering and playback components.

This module provides terminal-based ASCII art rendering and video playback:
- AsciiRenderer: Convert images to colored ASCII/Unicode art
- AsciiPlayer: Interactive terminal video player with keyboard controls
"""

from .renderer import AsciiRenderer, RenderMode, render_frame_to_terminal
from .player import (
    AsciiPlayer,
    AsciiPlayerConfig,
    HelpOverlay,
    KeyboardHandler,
    PlaybackController,
    PlaybackState,
    ProgressBarRenderer,
    ProgressBarState,
)

__all__ = [
    # Renderer
    "AsciiRenderer",
    "RenderMode",
    "render_frame_to_terminal",
    # Player
    "AsciiPlayer",
    "AsciiPlayerConfig",
    "HelpOverlay",
    "KeyboardHandler",
    "PlaybackController",
    "PlaybackState",
    "ProgressBarRenderer",
    "ProgressBarState",
]
