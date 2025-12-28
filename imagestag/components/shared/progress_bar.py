"""Progress bar renderer for GUI video players.

This module provides a progress bar that can be rendered as an Image
for use in pygame, tkinter, kivy, and other GUI backends.

Example:
    from imagestag.components.shared import ProgressBarRenderer, ProgressState

    renderer = ProgressBarRenderer(width=800, height=40)
    state = controller.get_progress_state()
    image = renderer.render(state)
    # Display image in your GUI
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imagestag import Image

from .playback import PlaybackState, ProgressState, format_time


@dataclass
class ProgressBarStyle:
    """Style configuration for progress bar."""

    # Colors (RGBA)
    background: tuple[int, int, int, int] = (30, 30, 30, 230)
    progress_fill: tuple[int, int, int, int] = (80, 180, 80, 255)
    progress_empty: tuple[int, int, int, int] = (60, 60, 60, 255)
    cursor: tuple[int, int, int, int] = (255, 200, 50, 255)
    seek_cursor: tuple[int, int, int, int] = (255, 100, 100, 255)
    text: tuple[int, int, int, int] = (220, 220, 220, 255)
    text_secondary: tuple[int, int, int, int] = (150, 150, 150, 255)

    # Dimensions
    bar_height: int = 6
    bar_margin: int = 10
    cursor_radius: int = 8

    # Font
    font_size: int = 14


class ProgressBarRenderer:
    """Render a progress bar as an Image.

    The progress bar includes:
    - Progress indicator
    - Current time / total time
    - Playback state icon
    - Speed indicator
    - FPS counter
    - Seek cursor (when seeking)
    """

    # Status icons (Unicode)
    ICONS = {
        PlaybackState.PLAYING: "\u25B6",  # Play
        PlaybackState.PAUSED: "\u23F8",  # Pause
        PlaybackState.STOPPED: "\u23F9",  # Stop
        PlaybackState.SEEKING: "\u23E9",  # Fast forward
    }

    def __init__(
        self,
        width: int = 800,
        height: int = 40,
        style: ProgressBarStyle | None = None,
    ):
        """Initialize progress bar renderer.

        :param width: Width in pixels
        :param height: Height in pixels
        :param style: Style configuration
        """
        self.width = width
        self.height = height
        self.style = style or ProgressBarStyle()
        self._font = None

    def resize(self, width: int, height: int) -> None:
        """Resize the progress bar."""
        self.width = width
        self.height = height

    def render(self, state: ProgressState) -> "Image":
        """Render progress bar to an Image.

        :param state: Current playback state
        :return: Image with rendered progress bar
        """
        from imagestag import Canvas, Anchor2D

        # Create canvas with background color
        canvas = Canvas(size=(self.width, self.height), default_color=self.style.background)
        s = self.style

        # Get font
        font = canvas.get_default_font(size=s.font_size)

        # Calculate layout
        margin = s.bar_margin
        bar_y = (self.height - s.bar_height) // 2

        # Left section: icon + time
        left_text = f"{self.ICONS.get(state.playback_state, '?')} {format_time(state.current_time)}"

        # Right section: speed + fps + total time
        speed_str = f"{state.playback_speed:.1f}x" if state.playback_speed != 1.0 else ""
        fps_str = f"{state.actual_fps:.0f}fps" if state.actual_fps > 0 else ""
        right_parts = [p for p in [speed_str, fps_str, format_time(state.total_time)] if p]
        right_text = " | ".join(right_parts)

        # Draw text
        text_y = self.height // 2

        # Left text
        canvas.text(
            pos=(margin, text_y),
            text=left_text,
            color=s.text,
            font=font,
            anchor=Anchor2D.CENTER_LEFT,
        )

        # Right text
        canvas.text(
            pos=(self.width - margin, text_y),
            text=right_text,
            color=s.text_secondary,
            font=font,
            anchor=Anchor2D.CENTER_RIGHT,
        )

        # Calculate bar position (between text areas)
        # Estimate text widths (rough approximation)
        left_width = len(left_text) * (s.font_size * 0.6)
        right_width = len(right_text) * (s.font_size * 0.6)

        bar_left = int(margin + left_width + margin)
        bar_right = int(self.width - margin - right_width - margin)
        bar_width = bar_right - bar_left

        if bar_width > 50:  # Only draw if enough space
            # Progress bar background
            canvas.rect(
                pos=(bar_left, bar_y),
                size=(bar_width, s.bar_height),
                color=s.progress_empty,
            )

            # Progress fill
            if state.total_time > 0:
                progress = state.current_time / state.total_time
                progress = max(0.0, min(1.0, progress))
                fill_width = int(bar_width * progress)

                if fill_width > 0:
                    canvas.rect(
                        pos=(bar_left, bar_y),
                        size=(fill_width, s.bar_height),
                        color=s.progress_fill,
                    )

                # Current position cursor
                cursor_x = bar_left + fill_width
                canvas.circle(
                    coord=(cursor_x, bar_y + s.bar_height // 2),
                    radius=s.cursor_radius,
                    color=s.cursor,
                )

                # Seek cursor (if seeking)
                if state.is_seeking and state.cursor_position is not None:
                    seek_x = bar_left + int(bar_width * state.cursor_position)
                    canvas.circle(
                        coord=(seek_x, bar_y + s.bar_height // 2),
                        radius=s.cursor_radius + 2,
                        color=s.seek_cursor,
                    )

        return canvas.to_image()

    def render_minimal(self, state: ProgressState) -> "Image":
        """Render a minimal progress bar (just the bar, no text).

        :param state: Current playback state
        :return: Image with rendered progress bar
        """
        from imagestag import Canvas

        # Create canvas with background color
        canvas = Canvas(size=(self.width, self.height), default_color=self.style.background)
        s = self.style

        # Bar
        margin = 4
        bar_height = self.height - 2 * margin

        # Progress bar background
        canvas.rect(
            pos=(margin, margin),
            size=(self.width - 2 * margin, bar_height),
            color=s.progress_empty,
        )

        # Progress fill
        if state.total_time > 0:
            progress = state.current_time / state.total_time
            progress = max(0.0, min(1.0, progress))
            fill_width = int((self.width - 2 * margin) * progress)

            if fill_width > 0:
                canvas.rect(
                    pos=(margin, margin),
                    size=(fill_width, bar_height),
                    color=s.progress_fill,
                )

        return canvas.to_image()
