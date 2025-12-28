"""Pygame-based StreamView implementation.

Provides a native pygame window for displaying StreamView layers.
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
    from imagestag.components.stream_view import StreamViewLayer


@dataclass
class StreamViewPygame(StreamViewBase):
    """Native pygame implementation of StreamView.

    Displays StreamView layers in a pygame window with keyboard/mouse handling.

    Example:
        from imagestag.components.pygame import StreamViewPygame
        from imagestag.streams import VideoStream

        video = VideoStream('video.mp4', loop=True)

        view = StreamViewPygame(1280, 720, title="My Player")
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
                         "native" for per-layer pygame drawing
        resizable: Whether window can be resized
    """

    # Pygame-specific attributes
    compositing_mode: Literal["python", "native"] = "python"
    resizable: bool = True

    # Pygame-specific state
    _screen: Any = field(default=None, repr=False)
    _clock: Any = field(default=None, repr=False)

    def run(self) -> None:
        """Run the main event loop (blocking).

        This initializes pygame, creates the window, and runs the
        render loop until stop() is called or window is closed.
        """
        try:
            import pygame
        except ImportError:
            raise ImportError(
                "pygame is required for StreamViewPygame. "
                "Install with: poetry install -E pygame"
            )

        # Initialize pygame
        pygame.init()

        # Create window
        flags = pygame.RESIZABLE if self.resizable else 0
        self._screen = pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption(self.title)

        self._clock = pygame.time.Clock()

        # Start layers
        self.start()

        # Main loop
        while self._running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    break

                elif event.type == pygame.VIDEORESIZE:
                    self._screen = pygame.display.set_mode(
                        (event.w, event.h),
                        pygame.RESIZABLE if self.resizable else 0
                    )
                    self._handle_resize(event.w, event.h)

                elif event.type in (pygame.KEYDOWN, pygame.KEYUP):
                    key_event = convert_key_event(event)
                    if key_event:
                        self._dispatch_key_event(key_event)

                elif event.type in (
                    pygame.MOUSEMOTION,
                    pygame.MOUSEBUTTONDOWN,
                    pygame.MOUSEBUTTONUP,
                    pygame.MOUSEWHEEL,
                ):
                    mouse_event = convert_mouse_event(event)
                    if mouse_event:
                        self._dispatch_mouse_event(mouse_event)

            if not self._running:
                break

            # Render frame
            if not self._paused:
                timestamp = time.perf_counter() - self._start_time
                self._render_frame(timestamp)

            # Cap frame rate
            self._clock.tick(self.target_fps)

        # Cleanup
        self.stop()
        pygame.quit()

    def run_async(self) -> threading.Thread:
        """Start the view in a background thread.

        :return: Thread running the view
        """
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

    def _render_frame(self, timestamp: float) -> None:
        """Render a single frame to the screen.

        :param timestamp: Current playback timestamp
        """
        import pygame

        if self.compositing_mode == "python":
            # Composite all layers to single Image, then blit
            composite = self._compositor.composite_rgb(timestamp)
            self._blit_image(composite)
        else:
            # Native mode: draw each layer separately
            self._screen.fill(self._compositor._background_color)
            for layer in self._compositor.layers:
                frame = self._compositor.get_layer_frame(layer, timestamp)
                if frame is not None:
                    self._blit_layer(frame, layer)

        pygame.display.flip()

    def _blit_image(self, image: "Image") -> None:
        """Blit an Image to the pygame screen.

        :param image: Image to display
        """
        import pygame
        import numpy as np

        # Get RGB pixels as numpy array
        pixels = image.convert('RGB').get_pixels()

        # Pygame expects (width, height, 3) but numpy gives (height, width, 3)
        # Use surfarray which handles this correctly
        surface = pygame.surfarray.make_surface(np.transpose(pixels, (1, 0, 2)))

        # Scale to screen size if needed
        if surface.get_size() != (self.width, self.height):
            surface = pygame.transform.scale(surface, (self.width, self.height))

        self._screen.blit(surface, (0, 0))

    def _blit_layer(self, image: "Image", layer: "StreamViewLayer") -> None:
        """Blit a layer's frame to the pygame screen.

        :param image: Frame image
        :param layer: Layer being rendered
        """
        import pygame
        import numpy as np

        # Calculate layer bounds
        layer_x = layer.x if layer.x is not None else 0
        layer_y = layer.y if layer.y is not None else 0
        layer_w = layer.width if layer.width is not None else self.width
        layer_h = layer.height if layer.height is not None else self.height

        # Get pixels
        pixels = image.convert('RGB').get_pixels()

        # Create surface
        surface = pygame.surfarray.make_surface(np.transpose(pixels, (1, 0, 2)))

        # Scale to layer size
        if surface.get_size() != (layer_w, layer_h):
            surface = pygame.transform.scale(surface, (layer_w, layer_h))

        self._screen.blit(surface, (layer_x, layer_y))
