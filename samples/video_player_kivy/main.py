#!/usr/bin/env python3
"""Video Player - Kivy Backend.

Full-featured video player with seeking, speed control, and progress bar.
Uses the shared PlaybackController for all backends.

Usage:
    poetry run python samples/video_player_kivy/main.py [video_path]

Controls:
    Space       - Play/Pause toggle
    Q / Escape  - Stop and exit
    Left/Right  - Seek backward/forward 5 seconds
    Shift+Left/Right - Fine seek 1 second
    Home/End    - Jump to start/end
    +/-         - Speed up/down
    H           - Toggle help overlay
    F           - Toggle fullscreen
    Click       - Seek to position on progress bar
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Default video path
DEFAULT_VIDEO = PROJECT_ROOT / "tmp" / "media" / "big_buck_bunny_1080p_h264.mov"

# Parse args before kivy imports (kivy eats args)
parser = argparse.ArgumentParser(description="Video Player - Kivy Backend")
parser.add_argument("video", nargs="?", default=str(DEFAULT_VIDEO), help="Path to video file")
parser.add_argument("--no-loop", action="store_true", help="Don't loop video")
args, _ = parser.parse_known_args()

video_path = Path(args.video)
if not video_path.exists():
    print(f"Error: Video not found: {video_path}")
    print("Run: python scripts/download_test_media.py")
    sys.exit(1)

# Set kivy config before import
import os
os.environ["KIVY_NO_ARGS"] = "1"

try:
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.graphics import Color, Rectangle
    from kivy.graphics.texture import Texture
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.label import Label
    from kivy.uix.slider import Slider
    from kivy.uix.widget import Widget
except ImportError:
    print("Error: Kivy is required. Install with: poetry add kivy")
    sys.exit(1)

from imagestag.streams import VideoStream
from imagestag.components.shared import (
    PlaybackController,
    PlaybackConfig,
    PlaybackState,
    format_time,
)


HELP_TEXT = """
VIDEO PLAYER CONTROLS

PLAYBACK
  Space         Play / Pause
  Q / Escape    Stop and exit

SEEKING
  Left / Right  Seek 5 seconds
  Home / End    Jump to start / end

SPEED
  + / =         Speed up
  - / _         Speed down

VIEW
  F             Toggle fullscreen
  H             Toggle this help

Press any key to close help
"""


class VideoWidget(Widget):
    """Widget for displaying video frames."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.texture = None
        self._rect = None

        with self.canvas:
            Color(0.08, 0.08, 0.1, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size
        if self._rect and self.texture:
            # Center the video
            tex_w, tex_h = self.texture.size
            scale_w = self.width / tex_w
            scale_h = self.height / tex_h
            scale = min(scale_w, scale_h)

            new_w = tex_w * scale
            new_h = tex_h * scale
            x = self.x + (self.width - new_w) / 2
            y = self.y + (self.height - new_h) / 2

            self._rect.pos = (x, y)
            self._rect.size = (new_w, new_h)

    def update_frame(self, frame):
        """Update the displayed frame."""
        if frame is None:
            return

        # Get pixels as RGB
        pixels = frame.get_pixels()
        if pixels.shape[2] == 4:
            pixels = pixels[:, :, :3]

        # Create or update texture
        h, w = pixels.shape[:2]

        if self.texture is None or self.texture.size != (w, h):
            self.texture = Texture.create(size=(w, h), colorfmt='rgb')
            self.texture.flip_vertical()

            # Create rectangle for displaying texture
            with self.canvas:
                Color(1, 1, 1, 1)
                self._rect = Rectangle(texture=self.texture, pos=self.pos, size=self.size)

        # Update texture data
        self.texture.blit_buffer(pixels.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        if self._rect:
            self._rect.texture = self.texture
            self._update_rect()


class VideoProgressBar(BoxLayout):
    """Progress bar with time display."""

    def __init__(self, controller, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=50, **kwargs)
        self.controller = controller
        self._dragging = False

        # Style
        with self.canvas.before:
            Color(0.16, 0.16, 0.19, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Left label
        self.left_label = Label(
            text="\u25B6  00:00",
            size_hint_x=None,
            width=120,
            halign='left',
            color=(0.86, 0.86, 0.88, 1),
        )
        self.left_label.bind(size=self.left_label.setter('text_size'))
        self.add_widget(self.left_label)

        # Slider
        self.slider = Slider(
            min=0,
            max=100,
            value=0,
            cursor_size=(20, 20),
        )
        self.slider.bind(on_touch_down=self._on_slider_down)
        self.slider.bind(on_touch_up=self._on_slider_up)
        self.add_widget(self.slider)

        # Right label
        self.right_label = Label(
            text="00:00",
            size_hint_x=None,
            width=150,
            halign='right',
            color=(0.55, 0.55, 0.57, 1),
        )
        self.right_label.bind(size=self.right_label.setter('text_size'))
        self.add_widget(self.right_label)

    def _update_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _on_slider_down(self, slider, touch):
        if slider.collide_point(*touch.pos):
            self._dragging = True

    def _on_slider_up(self, slider, _touch):
        if self._dragging:
            self._dragging = False
            progress = slider.value / 100
            self.controller.seek_to(progress * self.controller.duration)

    def update(self):
        """Update progress bar display."""
        state = self.controller.get_progress_state()

        # Icon
        icons = {
            PlaybackState.PLAYING: "\u25B6",
            PlaybackState.PAUSED: "\u23F8",
            PlaybackState.STOPPED: "\u23F9",
        }
        icon = icons.get(state.playback_state, "?")
        self.left_label.text = f"{icon}  {format_time(state.current_time)}"

        # Right label
        parts = []
        if state.playback_speed != 1.0:
            parts.append(f"{state.playback_speed:.1f}x")
        if state.actual_fps > 0:
            parts.append(f"{state.actual_fps:.0f}fps")
        parts.append(format_time(state.total_time))
        self.right_label.text = "  |  ".join(parts)

        # Slider
        if not self._dragging and state.total_time > 0:
            progress = (state.current_time / state.total_time) * 100
            self.slider.value = progress


class HelpOverlay(FloatLayout):
    """Help overlay."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0.12, 0.12, 0.16, 0.95)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.label = Label(
            text=HELP_TEXT,
            font_name='RobotoMono',
            font_size=14,
            halign='left',
            valign='middle',
            color=(0.86, 0.86, 0.88, 1),
        )
        self.label.bind(size=self._update_label_size)
        self.add_widget(self.label)

    def _update_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _update_label_size(self, *_args):
        self.label.text_size = (self.width - 100, None)


class VideoPlayerApp(App):
    """Kivy video player application."""

    def __init__(self, video_path: Path, loop: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.video_path = video_path
        self.loop = loop
        self.show_help = False

    def build(self):
        # Create video and controller
        self.video = VideoStream(str(self.video_path), loop=self.loop)
        self.config_playback = PlaybackConfig(seek_step=5.0, fine_seek_step=1.0)
        self.controller = PlaybackController(self.video, self.config_playback)

        # Main layout
        self.root_layout = FloatLayout()

        # Video + controls layout
        self.main_layout = BoxLayout(orientation='vertical')
        self.root_layout.add_widget(self.main_layout)

        # Video widget
        self.video_widget = VideoWidget()
        self.main_layout.add_widget(self.video_widget)

        # Progress bar
        self.progress_bar = VideoProgressBar(self.controller)
        self.main_layout.add_widget(self.progress_bar)

        # Help overlay (hidden initially)
        self.help_overlay = None

        # Bind keyboard
        Window.bind(on_keyboard=self._on_keyboard)

        # Set window title
        self.title = f"Video Player - {self.video_path.name}"

        # Start playback
        self.controller.play()

        # Schedule updates
        Clock.schedule_interval(self._update, 1/60)

        return self.root_layout

    def _on_keyboard(self, window, key, scancode, codepoint, modifier):
        """Handle keyboard input."""
        if self.show_help:
            self._hide_help()
            return True

        shift = 'shift' in modifier

        # Escape or Q
        if key == 27 or codepoint == 'q':
            self.stop()
            return True

        # Space
        if key == 32:
            self.controller.toggle()
            return True

        # Arrow keys
        if key == 276:  # Left
            if shift:
                self.controller.seek_relative(-self.config_playback.fine_seek_step)
            else:
                self.controller.seek_backward()
            return True

        if key == 275:  # Right
            if shift:
                self.controller.seek_relative(self.config_playback.fine_seek_step)
            else:
                self.controller.seek_forward()
            return True

        # Home/End
        if key == 278:  # Home
            self.controller.seek_to_start()
            return True

        if key == 279:  # End
            self.controller.seek_to_end()
            return True

        # Speed
        if codepoint in ('+', '='):
            self.controller.speed_up()
            return True

        if codepoint == '-':
            self.controller.speed_down()
            return True

        # Help
        if codepoint == 'h':
            self._toggle_help()
            return True

        # Fullscreen
        if codepoint == 'f':
            Window.fullscreen = not Window.fullscreen
            return True

        return False

    def _toggle_help(self):
        if self.show_help:
            self._hide_help()
        else:
            self._show_help()

    def _show_help(self):
        self.show_help = True
        self.help_overlay = HelpOverlay()
        self.root_layout.add_widget(self.help_overlay)

    def _hide_help(self):
        self.show_help = False
        if self.help_overlay:
            self.root_layout.remove_widget(self.help_overlay)
            self.help_overlay = None

    def _update(self, _dt):
        """Update loop."""
        # Get frame
        frame, _ = self.controller.get_frame()

        if frame is not None:
            self.controller.update_fps()
            self.video_widget.update_frame(frame)

        # Update progress bar
        self.progress_bar.update()

    def on_stop(self):
        """Cleanup on exit."""
        self.controller.stop()


def main():
    app = VideoPlayerApp(video_path, loop=not args.no_loop)
    app.run()


if __name__ == "__main__":
    main()
