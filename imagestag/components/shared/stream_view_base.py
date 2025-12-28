"""Base class for native StreamView backends.

Provides shared functionality for pygame, tkinter, kivy, and PIL backends.
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from .compositor import LayerCompositor, Viewport
from .base_events import KeyEvent, MouseEvent, ResizeEvent

if TYPE_CHECKING:
    from imagestag import Image
    from imagestag.components.stream_view import StreamViewLayer
    from imagestag.streams import ImageStream
    from imagestag.filters import FilterPipeline


@dataclass
class StreamViewBase(ABC):
    """Base class for native StreamView backends.

    Provides common functionality for layer management, viewport control,
    event handling, and lifecycle management. Subclasses implement the
    backend-specific rendering and event loop.

    Attributes:
        width: View width in pixels
        height: View height in pixels
        title: Window title (for windowed backends)
        target_fps: Target frame rate for rendering
    """

    width: int = 1280
    height: int = 720
    title: str = "StreamView"
    target_fps: int = 60

    # Internal state
    _compositor: LayerCompositor = field(init=False, repr=False)
    _layers: dict[str, "StreamViewLayer"] = field(default_factory=dict, repr=False)
    _running: bool = field(default=False, repr=False)
    _paused: bool = field(default=False, repr=False)
    _start_time: float = field(default=0.0, repr=False)

    # Event handlers
    _key_handlers: list[Callable[[KeyEvent], None]] = field(default_factory=list, repr=False)
    _mouse_handlers: list[Callable[[MouseEvent], None]] = field(default_factory=list, repr=False)
    _resize_handlers: list[Callable[[ResizeEvent], None]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Initialize compositor and handler lists."""
        self._compositor = LayerCompositor(self.width, self.height)
        self._layers = {}
        self._key_handlers = []
        self._mouse_handlers = []
        self._resize_handlers = []

    # -------------------------------------------------------------------------
    # Layer Management
    # -------------------------------------------------------------------------

    def add_layer(
        self,
        *,
        stream: "ImageStream | None" = None,
        image: "Image | None" = None,
        url: str | None = None,
        source_layer: "StreamViewLayer | None" = None,
        pipeline: "FilterPipeline | None" = None,
        z_index: int = 0,
        target_fps: int = 60,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
        depth: float = 1.0,
        name: str = "",
        buffer_size: int = 4,
    ) -> "StreamViewLayer":
        """Add a layer to the view.

        :param stream: ImageStream source (VideoStream, CameraStream, etc.)
        :param image: Static Image source
        :param url: Static URL source (not recommended for native backends)
        :param source_layer: Another layer to derive content from
        :param pipeline: FilterPipeline to apply to frames
        :param z_index: Stacking order (higher = on top)
        :param target_fps: Target FPS for this layer
        :param x: X position (None = fill width)
        :param y: Y position (None = fill height)
        :param width: Layer width (None = fill width)
        :param height: Layer height (None = fill height)
        :param depth: Viewport depth (0.0=fixed, 1.0=content)
        :param name: Display name for debugging
        :param buffer_size: Frame buffer size
        :return: Created StreamViewLayer
        """
        from imagestag.components.stream_view import StreamViewLayer

        layer = StreamViewLayer(
            stream=stream,
            image=image,
            url=url,
            source_layer=source_layer,
            pipeline=pipeline,
            z_index=z_index,
            target_fps=target_fps,
            x=x,
            y=y,
            width=width,
            height=height,
            depth=depth,
            name=name,
            buffer_size=buffer_size,
        )

        self._layers[layer.id] = layer
        self._compositor.add_layer(layer)

        return layer

    def remove_layer(self, layer_id: str) -> None:
        """Remove a layer by ID.

        :param layer_id: Layer ID to remove
        """
        layer = self._layers.pop(layer_id, None)
        if layer:
            layer.stop()
            self._compositor.remove_layer(layer_id)

    def get_layer(self, layer_id: str) -> "StreamViewLayer | None":
        """Get a layer by ID.

        :param layer_id: Layer ID
        :return: StreamViewLayer or None
        """
        return self._layers.get(layer_id)

    @property
    def layers(self) -> list["StreamViewLayer"]:
        """Get all layers sorted by z_index."""
        return sorted(self._layers.values(), key=lambda l: l.z_index)

    # -------------------------------------------------------------------------
    # Viewport Control
    # -------------------------------------------------------------------------

    @property
    def viewport(self) -> Viewport:
        """Get the viewport for zoom/pan control."""
        return self._compositor.viewport

    def set_zoom(self, zoom: float, cx: float = 0.5, cy: float = 0.5) -> None:
        """Set zoom level centered on a point.

        :param zoom: Zoom level (1.0 = no zoom)
        :param cx: Center X (0.0-1.0)
        :param cy: Center Y (0.0-1.0)
        """
        self._compositor.viewport.set_zoom(zoom, cx, cy)
        self._compositor.update_viewports()

    def reset_zoom(self) -> None:
        """Reset to no zoom."""
        self._compositor.viewport.reset()
        self._compositor.update_viewports()

    # -------------------------------------------------------------------------
    # Event Handlers (Decorators)
    # -------------------------------------------------------------------------

    def on_key(self, handler: Callable[[KeyEvent], None]) -> Callable[[KeyEvent], None]:
        """Decorator to register a key event handler.

        Example:
            @view.on_key
            def handle_key(event):
                if event.key == 'q':
                    view.stop()
        """
        self._key_handlers.append(handler)
        return handler

    def on_mouse(self, handler: Callable[[MouseEvent], None]) -> Callable[[MouseEvent], None]:
        """Decorator to register a mouse event handler."""
        self._mouse_handlers.append(handler)
        return handler

    def on_resize(self, handler: Callable[[ResizeEvent], None]) -> Callable[[ResizeEvent], None]:
        """Decorator to register a resize event handler."""
        self._resize_handlers.append(handler)
        return handler

    # -------------------------------------------------------------------------
    # Lifecycle Management
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start all layer producers (but don't start main loop)."""
        self._running = True
        self._paused = False
        self._start_time = time.perf_counter()

        for layer in self._layers.values():
            layer.start()

    def stop(self) -> None:
        """Stop playback and close window."""
        self._running = False

        for layer in self._layers.values():
            layer.stop()

    def pause(self) -> None:
        """Pause playback (layers stop updating)."""
        self._paused = True
        for layer in self._layers.values():
            if layer.stream is not None and hasattr(layer.stream, 'pause'):
                layer.stream.pause()

    def resume(self) -> None:
        """Resume playback after pause."""
        self._paused = False
        for layer in self._layers.values():
            if layer.stream is not None and hasattr(layer.stream, 'resume'):
                layer.stream.resume()

    def toggle_pause(self) -> None:
        """Toggle pause state."""
        if self._paused:
            self.resume()
        else:
            self.pause()

    @property
    def is_paused(self) -> bool:
        """Whether playback is paused."""
        return self._paused

    @property
    def is_running(self) -> bool:
        """Whether the view is running."""
        return self._running

    @property
    def elapsed_time(self) -> float:
        """Seconds since start."""
        if self._start_time == 0.0:
            return 0.0
        return time.perf_counter() - self._start_time

    # -------------------------------------------------------------------------
    # Abstract Methods (Backend-Specific)
    # -------------------------------------------------------------------------

    @abstractmethod
    def run(self) -> None:
        """Run the main event loop (blocking).

        Subclasses implement the backend-specific event loop and rendering.
        """
        ...

    @abstractmethod
    def run_async(self) -> threading.Thread:
        """Start the view in a background thread.

        :return: Thread running the view
        """
        ...

    # -------------------------------------------------------------------------
    # Helper Methods for Event Dispatch
    # -------------------------------------------------------------------------

    def _dispatch_key_event(self, event: KeyEvent) -> None:
        """Dispatch a key event to all handlers.

        :param event: KeyEvent to dispatch
        """
        for handler in self._key_handlers:
            try:
                handler(event)
            except Exception:
                pass

    def _dispatch_mouse_event(self, event: MouseEvent) -> None:
        """Dispatch a mouse event to all handlers.

        :param event: MouseEvent to dispatch
        """
        for handler in self._mouse_handlers:
            try:
                handler(event)
            except Exception:
                pass

    def _dispatch_resize_event(self, event: ResizeEvent) -> None:
        """Dispatch a resize event to all handlers.

        :param event: ResizeEvent to dispatch
        """
        for handler in self._resize_handlers:
            try:
                handler(event)
            except Exception:
                pass

    def _handle_resize(self, new_width: int, new_height: int) -> None:
        """Handle a window resize.

        :param new_width: New width in pixels
        :param new_height: New height in pixels
        """
        old_w, old_h = self.width, self.height
        self.width, self.height = new_width, new_height
        self._compositor.set_size(self.width, self.height)

        resize_event = ResizeEvent(
            width=self.width,
            height=self.height,
            old_width=old_w,
            old_height=old_h,
        )
        self._dispatch_resize_event(resize_event)
