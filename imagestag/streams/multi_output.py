"""Multi-output stream implementation.

Provides MultiOutputStream for generators that produce multiple layer outputs
with different formats (jpeg, png, svg) in a background thread.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from .base import ImageStream

if TYPE_CHECKING:
    from imagestag import Image


@dataclass
class LayerConfig:
    """Configuration for an output layer.

    Attributes:
        format: Output format ("jpeg", "png", "svg")
        quality: JPEG quality (1-100), ignored for png/svg
        z_index: Stacking order for this layer
        depth: Viewport depth (0.0=fixed, 1.0=follows content zoom)
    """

    format: Literal["jpeg", "png", "svg"] = "png"
    quality: int = 85
    z_index: int = 0
    depth: float = 1.0


@dataclass
class LayerOutput:
    """Output target for a single layer.

    Write to this from render() to update the layer content.

    Attributes:
        name: Layer identifier
        config: Layer configuration (format, quality, z_index)
        image: Current image content (for jpeg/png layers)
        svg: Current SVG content (for svg layers)
        dirty: Whether content has been updated since last read
    """

    name: str
    config: LayerConfig = field(default_factory=LayerConfig)

    # Content
    image: "Image | None" = field(default=None, repr=False)
    svg: str | None = field(default=None, repr=False)

    # State
    dirty: bool = field(default=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set_image(
        self,
        image: "Image",
        format: Literal["jpeg", "png"] | None = None,
        quality: int | None = None,
    ) -> None:
        """Set image content for this layer.

        :param image: Image to display
        :param format: Override format (jpeg/png)
        :param quality: Override JPEG quality
        """
        with self._lock:
            self.image = image
            self.svg = None
            if format is not None:
                self.config.format = format
            if quality is not None:
                self.config.quality = quality
            self.dirty = True

    def set_svg(self, svg: str) -> None:
        """Set SVG content for this layer.

        :param svg: SVG string content
        """
        with self._lock:
            self.svg = svg
            self.image = None
            self.config.format = "svg"
            self.dirty = True

    def clear(self) -> None:
        """Clear layer content."""
        with self._lock:
            self.image = None
            self.svg = None
            self.dirty = True

    def get_content(self) -> tuple["Image | None", str | None, bool]:
        """Get current content atomically.

        :return: Tuple of (image, svg, was_dirty)
        """
        with self._lock:
            was_dirty = self.dirty
            self.dirty = False
            return self.image, self.svg, was_dirty


class RenderContext(dict):
    """Context passed to render() providing access to output layers.

    Access layers by name: ctx["background"], ctx["overlay"], etc.
    Or as attributes: ctx.background, ctx.overlay (if valid Python identifiers).

    Attributes:
        timestamp: Current render timestamp
        frame_index: Current frame number
        elapsed: Time since start
    """

    def __init__(self, outputs: dict[str, LayerOutput]):
        super().__init__(outputs)
        self.timestamp: float = 0.0
        self.frame_index: int = 0
        self.elapsed: float = 0.0

    def __getattr__(self, name: str) -> LayerOutput:
        if name in self:
            return self[name]
        raise AttributeError(f"No output layer named '{name}'")


class MultiOutputStream(ImageStream):
    """Stream that renders to multiple output layers.

    Subclass and override render() to write to multiple layers. Each layer
    can have different encoding (jpeg for backgrounds, png for overlays,
    svg for vector graphics).

    The stream runs in a background thread at a target FPS, continuously
    calling render() and updating layer outputs.

    Example:
        class SceneRenderer(MultiOutputStream):
            outputs = {
                "background": LayerConfig(format="jpeg", quality=60, z_index=0),
                "annotations": LayerConfig(format="png", z_index=1),
                "vectors": LayerConfig(format="svg", z_index=2),
            }

            def __init__(self, width: int, height: int):
                super().__init__()
                self.width = width
                self.height = height

            def render(self, ctx: RenderContext) -> None:
                # Render background (compressed jpeg)
                ctx["background"].set_image(self._render_bg(ctx.timestamp))

                # Render annotations with transparency (png)
                ctx["annotations"].set_image(self._render_annotations(ctx.timestamp))

                # Render vector overlay (svg)
                ctx["vectors"].set_svg(self._generate_svg(ctx.timestamp))

        # Usage
        renderer = SceneRenderer(1280, 720)
        renderer.start()  # Starts background render thread

        # Access outputs
        for name, output in renderer.layer_outputs.items():
            image, svg, dirty = output.get_content()

    Attributes:
        outputs: Dict of layer name -> LayerConfig (override in subclass)
        target_fps: Target frames per second for background rendering
    """

    # Override in subclass to define output layers
    outputs: dict[str, LayerConfig] = {}

    def __init__(self, target_fps: float = 30.0) -> None:
        """Initialize multi-output stream.

        :param target_fps: Target FPS for background rendering
        """
        super().__init__()
        self.target_fps = target_fps

        # Create layer outputs from class definition
        self._layer_outputs: dict[str, LayerOutput] = {}
        for name, config in self.outputs.items():
            self._layer_outputs[name] = LayerOutput(name=name, config=config)

        # Create render context
        self._render_ctx = RenderContext(self._layer_outputs)

        # Background thread state
        self._render_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def layer_outputs(self) -> dict[str, LayerOutput]:
        """Access to layer outputs for reading content."""
        return self._layer_outputs

    def render(self, ctx: RenderContext) -> None:
        """Override to render content to output layers.

        :param ctx: Render context with access to layer outputs
        """
        pass

    def start(self) -> None:
        """Start the background render thread."""
        if self._running:
            return

        super().start()
        self._stop_event.clear()

        self._render_thread = threading.Thread(
            target=self._render_loop,
            daemon=True,
            name=f"MultiOutputStream-{id(self)}",
        )
        self._render_thread.start()

    def stop(self) -> None:
        """Stop the background render thread."""
        self._stop_event.set()

        if self._render_thread is not None:
            self._render_thread.join(timeout=1.0)
            self._render_thread = None

        super().stop()

    def _render_loop(self) -> None:
        """Background render loop."""
        frame_interval = 1.0 / self.target_fps
        frame_index = 0

        while not self._stop_event.is_set():
            if self._paused:
                time.sleep(0.01)
                continue

            loop_start = time.perf_counter()

            # Update context
            self._render_ctx.timestamp = self.elapsed_time
            self._render_ctx.frame_index = frame_index
            self._render_ctx.elapsed = self.elapsed_time

            # Call render
            try:
                self.render(self._render_ctx)
            except Exception:
                pass  # Don't crash on render errors

            # Increment frame
            frame_index += 1
            self._frame_index = frame_index

            # Notify subscribers
            self._notify_subscribers()

            # Sleep to maintain FPS
            elapsed = time.perf_counter() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def get_frame(self, timestamp: float) -> tuple["Image | None", int]:
        """Get the primary output frame.

        Returns the first image layer output, or None if no image outputs.

        :param timestamp: Ignored (uses internal timing)
        :return: Tuple of (image, frame_index)
        """
        # Return first image output
        for output in self._layer_outputs.values():
            if output.image is not None:
                return (output.image, self._frame_index)

        return (None, self._frame_index)

    def get_output(self, name: str) -> LayerOutput | None:
        """Get a specific layer output by name.

        :param name: Layer name
        :return: LayerOutput or None
        """
        return self._layer_outputs.get(name)
