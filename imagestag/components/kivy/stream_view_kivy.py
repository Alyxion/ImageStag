"""Kivy-based StreamView implementation.

Provides a native kivy window for displaying StreamView layers.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from ..shared import ResizeEvent
from ..shared.stream_view_base import StreamViewBase
from .events import convert_key_event, convert_mouse_event

if TYPE_CHECKING:
    from imagestag import Image


@dataclass
class StreamViewKivy(StreamViewBase):
    """Native kivy implementation of StreamView.

    Displays StreamView layers in a kivy window with keyboard/mouse handling.

    Example:
        from imagestag.components.kivy import StreamViewKivy
        from imagestag.streams import VideoStream

        video = VideoStream('video.mp4', loop=True)

        view = StreamViewKivy(1280, 720, title="My Player")
        view.add_layer(stream=video, z_index=0)

        @view.on_key
        def handle_key(event):
            if event.key == 'q':
                view.stop()

        view.run()

    Attributes:
        width: Window width in pixels
        height: Window height in pixels
        title: Window title
        target_fps: Target frame rate for rendering
        compositing_mode: "python" for single-image compositing,
                         "native" for per-layer kivy drawing
        resizable: Whether window can be resized
    """

    # Kivy-specific attributes
    compositing_mode: Literal["python", "native"] = "python"
    resizable: bool = True

    # Kivy-specific state
    _app: Any = field(default=None, repr=False)
    _texture: Any = field(default=None, repr=False)

    def stop(self) -> None:
        """Stop playback and close window."""
        super().stop()
        if self._app:
            from kivy.app import App
            App.get_running_app().stop()

    def run(self) -> None:
        """Run the main event loop (blocking).

        This creates the kivy application and runs until
        stop() is called or window is closed.
        """
        try:
            # Configure kivy before importing other kivy modules
            import os
            os.environ.setdefault('KIVY_NO_ARGS', '1')

            from kivy.app import App
            from kivy.uix.widget import Widget
            from kivy.core.window import Window
            from kivy.graphics import Rectangle
            from kivy.graphics.texture import Texture
            from kivy.clock import Clock
        except ImportError:
            raise ImportError(
                "kivy is required for StreamViewKivy. "
                "Install with: poetry install -E kivy"
            )

        # Store reference to self for inner class
        view = self

        class StreamViewWidget(Widget):
            """Kivy widget that displays the composited frames."""

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self._texture = None
                self._rect = None

                # Create initial graphics
                with self.canvas:
                    self._rect = Rectangle(pos=self.pos, size=self.size)

                # Bind size/pos changes
                self.bind(pos=self._update_rect, size=self._update_rect)

            def _update_rect(self, *args):
                if self._rect:
                    self._rect.pos = self.pos
                    self._rect.size = self.size

            def update_texture(self, image: "Image"):
                """Update the texture with a new image.

                :param image: RGB Image to display
                """
                import numpy as np

                # Get RGB pixels
                pixels = image.convert('RGB').get_pixels()

                # Kivy textures use bottom-left origin, flip vertically
                pixels = np.flipud(pixels)

                # Create or update texture
                if self._texture is None or \
                   self._texture.size != (image.width, image.height):
                    self._texture = Texture.create(
                        size=(image.width, image.height),
                        colorfmt='rgb',
                    )

                # Update texture data
                self._texture.blit_buffer(
                    pixels.tobytes(),
                    colorfmt='rgb',
                    bufferfmt='ubyte',
                )

                # Update rectangle
                if self._rect:
                    self._rect.texture = self._texture

        class StreamViewApp(App):
            """Kivy application wrapper."""

            def build(self):
                # Set window properties
                Window.size = (view.width, view.height)
                Window.set_title(view.title)

                # Create widget
                self.widget = StreamViewWidget()

                # Bind keyboard
                Window.bind(on_key_down=self._on_key_down)
                Window.bind(on_key_up=self._on_key_up)
                Window.bind(on_resize=self._on_resize)

                # Bind mouse/touch
                self.widget.bind(on_touch_down=self._on_touch_down)
                self.widget.bind(on_touch_up=self._on_touch_up)
                self.widget.bind(on_touch_move=self._on_touch_move)

                # Start layers
                view.start()

                # Schedule render loop
                Clock.schedule_interval(self._render_tick, 1.0 / view.target_fps)

                return self.widget

            def _render_tick(self, dt):
                if not view._running:
                    App.get_running_app().stop()
                    return

                if not view._paused:
                    timestamp = time.perf_counter() - view._start_time
                    composite = view._compositor.composite_rgb(timestamp)
                    self.widget.update_texture(composite)

            def _on_key_down(self, window, keycode, scancode, text, modifiers):
                key_event = convert_key_event(
                    (keycode, text or ''),
                    text=text,
                    modifiers=modifiers,
                    is_press=True,
                )
                view._dispatch_key_event(key_event)
                return True

            def _on_key_up(self, window, keycode, scancode):
                key_event = convert_key_event(
                    (keycode, ''),
                    is_press=False,
                )
                view._dispatch_key_event(key_event)
                return True

            def _on_resize(self, window, width, height):
                view._handle_resize(width, height)

            def _on_touch_down(self, widget, touch):
                button = 'left'
                if touch.button:
                    button = touch.button

                mouse_event = convert_mouse_event(
                    touch.x, touch.y,
                    button=button,
                    event_type="press",
                    window_height=view.height,
                )
                view._dispatch_mouse_event(mouse_event)

            def _on_touch_up(self, widget, touch):
                button = 'left'
                if touch.button:
                    button = touch.button

                mouse_event = convert_mouse_event(
                    touch.x, touch.y,
                    button=button,
                    event_type="release",
                    window_height=view.height,
                )
                view._dispatch_mouse_event(mouse_event)

            def _on_touch_move(self, widget, touch):
                mouse_event = convert_mouse_event(
                    touch.x, touch.y,
                    event_type="move",
                    window_height=view.height,
                )
                view._dispatch_mouse_event(mouse_event)

            def on_stop(self):
                view._running = False
                for layer in view._layers.values():
                    layer.stop()

        # Run the app
        self._app = StreamViewApp()
        self._app.run()

    def run_async(self) -> threading.Thread:
        """Start the view in a background thread.

        Note: Kivy has thread restrictions. This may not work
        correctly on all platforms.

        :return: Thread running the view
        """
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread
