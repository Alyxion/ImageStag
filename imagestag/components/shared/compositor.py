"""Layer compositor for native StreamView implementations.

Composites StreamViewLayers into a single Image for native rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imagestag import Image
    from imagestag.components.stream_view import StreamViewLayer


@dataclass
class Viewport:
    """Viewport state for pan/zoom control.

    Coordinates are normalized (0.0 to 1.0) representing
    the visible portion of the content.

    Attributes:
        x: Left edge of visible area (0.0 = left edge)
        y: Top edge of visible area (0.0 = top edge)
        width: Width of visible area (1.0 = full width)
        height: Height of visible area (1.0 = full height)
        zoom: Zoom level (1.0 = no zoom, 2.0 = 2x zoom)
    """
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    zoom: float = 1.0

    def set_zoom(self, zoom: float, center_x: float = 0.5, center_y: float = 0.5) -> None:
        """Set zoom level centered on a point.

        :param zoom: New zoom level (clamped to 1.0-10.0)
        :param center_x: X center point for zoom (0.0-1.0)
        :param center_y: Y center point for zoom (0.0-1.0)
        """
        zoom = max(1.0, min(10.0, zoom))

        new_width = 1.0 / zoom
        new_height = 1.0 / zoom

        # Center on the given point
        self.x = max(0.0, min(1.0 - new_width, center_x - new_width / 2))
        self.y = max(0.0, min(1.0 - new_height, center_y - new_height / 2))
        self.width = new_width
        self.height = new_height
        self.zoom = zoom

    def pan(self, dx: float, dy: float) -> None:
        """Pan the viewport by normalized delta amounts.

        :param dx: Horizontal pan (positive = move right)
        :param dy: Vertical pan (positive = move down)
        """
        self.x = max(0.0, min(1.0 - self.width, self.x + dx))
        self.y = max(0.0, min(1.0 - self.height, self.y + dy))

    def reset(self) -> None:
        """Reset viewport to default (no zoom, no pan)."""
        self.x = 0.0
        self.y = 0.0
        self.width = 1.0
        self.height = 1.0
        self.zoom = 1.0


@dataclass
class LayerCompositor:
    """Composites StreamViewLayers into a single Image.

    This class is used by native StreamView implementations (pygame, tkinter, kivy)
    to render multiple layers into a single output image.

    Example:
        compositor = LayerCompositor(1280, 720)
        compositor.add_layer(layer1)
        compositor.add_layer(layer2)

        # In render loop:
        output = compositor.composite()
        # ... draw output to native canvas
    """

    width: int = 1280
    height: int = 720
    viewport: Viewport = field(default_factory=Viewport)
    _layers: dict[str, "StreamViewLayer"] = field(default_factory=dict, repr=False)
    _background_color: tuple[int, int, int] = (0, 0, 0)
    _frame_cache: dict[str, "Image"] = field(default_factory=dict, repr=False)

    def set_size(self, width: int, height: int) -> None:
        """Update output size.

        :param width: New width in pixels
        :param height: New height in pixels
        """
        self.width = width
        self.height = height

    def set_background(self, r: int, g: int, b: int) -> None:
        """Set background color for areas not covered by layers.

        :param r: Red (0-255)
        :param g: Green (0-255)
        :param b: Blue (0-255)
        """
        self._background_color = (r, g, b)

    def add_layer(self, layer: "StreamViewLayer") -> None:
        """Add a layer to the compositor.

        :param layer: StreamViewLayer to add
        """
        self._layers[layer.id] = layer
        # Update layer's viewport reference
        layer.set_viewport(self.viewport)

    def remove_layer(self, layer_id: str) -> None:
        """Remove a layer by ID.

        :param layer_id: Layer ID to remove
        """
        self._layers.pop(layer_id, None)
        self._frame_cache.pop(layer_id, None)

    def get_layer(self, layer_id: str) -> "StreamViewLayer | None":
        """Get a layer by ID.

        :param layer_id: Layer ID
        :return: StreamViewLayer or None if not found
        """
        return self._layers.get(layer_id)

    @property
    def layers(self) -> list["StreamViewLayer"]:
        """Get all layers sorted by z_index."""
        return sorted(self._layers.values(), key=lambda l: l.z_index)

    def update_viewports(self) -> None:
        """Update viewport on all layers."""
        for layer in self._layers.values():
            layer.set_viewport(self.viewport)

    def get_layer_frame(self, layer: "StreamViewLayer", timestamp: float) -> "Image | None":
        """Get current frame from a layer.

        Gets the raw Image from the layer's source, applying the layer's
        filter pipeline if present. Caches frames to avoid flickering when
        streams return None for unchanged frames.

        :param layer: Layer to get frame from
        :param timestamp: Current playback timestamp
        :return: Image frame or None if no frame available
        """
        from imagestag import Image

        frame: Image | None = None

        # Get frame based on source type
        if layer.stream is not None:
            result = layer.stream.get_frame(timestamp)

            # New API: get_frame returns tuple[Image | None, int]
            if isinstance(result, tuple) and len(result) == 2:
                frame, _frame_index = result
            else:
                # Fallback for any unexpected return type
                frame = result if not isinstance(result, tuple) else None

            # If stream returns None, use cached frame
            if frame is None:
                return self._frame_cache.get(layer.id)

        elif layer.source_layer is not None:
            # Derived layer - get frame from source layer
            frame = self.get_layer_frame(layer.source_layer, timestamp)

        elif layer.image is not None:
            # Static image
            frame = layer.image

        elif layer.url is not None:
            # URL source - can't load raw frame, return None
            # Native backends should handle URL differently
            return None

        if frame is None:
            # Return cached frame if available
            return self._frame_cache.get(layer.id)

        # Apply filter pipeline if present
        if layer.pipeline is not None:
            try:
                for f in layer.pipeline.filters:
                    frame = f.apply(frame)
            except Exception:
                pass  # Use unfiltered frame on error

        # Cache the frame for next time
        self._frame_cache[layer.id] = frame

        return frame

    def composite(self, timestamp: float = 0.0) -> "Image":
        """Composite all layers into a single output Image.

        Layers are composited in z_index order (lowest first).
        Each layer's position, size, and depth are respected.

        :param timestamp: Current playback timestamp (for stream frames)
        :return: Composited Image
        """
        from imagestag import Image
        import numpy as np

        # Create background canvas
        canvas = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        canvas[:, :, 0] = self._background_color[0]
        canvas[:, :, 1] = self._background_color[1]
        canvas[:, :, 2] = self._background_color[2]
        canvas[:, :, 3] = 255  # Fully opaque background

        # Sort layers by z_index
        sorted_layers = sorted(self._layers.values(), key=lambda l: l.z_index)

        for layer in sorted_layers:
            frame = self.get_layer_frame(layer, timestamp)
            if frame is None:
                continue

            # Calculate layer position and size
            layer_x = layer.x if layer.x is not None else 0
            layer_y = layer.y if layer.y is not None else 0
            layer_w = layer.width if layer.width is not None else self.width
            layer_h = layer.height if layer.height is not None else self.height

            # Apply viewport cropping based on layer depth (only when zoomed)
            eff_zoom = layer.effective_zoom
            if eff_zoom > 1.0 and layer.depth != 0.0:
                # Crop frame according to effective viewport
                x1, y1, x2, y2 = layer.get_effective_crop(frame.width, frame.height)
                # Ensure bounds are valid
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(frame.width, x2)
                y2 = min(frame.height, y2)
                # Ensure we have a valid region (at least 1x1)
                if x2 <= x1:
                    x2 = min(x1 + 1, frame.width)
                    x1 = x2 - 1
                if y2 <= y1:
                    y2 = min(y1 + 1, frame.height)
                    y1 = y2 - 1
                # Only crop if we have a valid region
                if x2 > x1 and y2 > y1 and x1 >= 0 and y1 >= 0:
                    try:
                        frame = frame.cropped((x1, y1, x2, y2))
                    except ValueError:
                        pass  # Skip crop on error, use full frame

            # Resize frame to layer size
            if frame.width != layer_w or frame.height != layer_h:
                frame = frame.resized((layer_w, layer_h))

            # Get frame pixels in RGBA format
            frame_rgba = frame.convert('RGBA')
            frame_pixels = frame_rgba.get_pixels()

            # Calculate blending region (clamp to canvas bounds)
            dst_x1 = max(0, layer_x)
            dst_y1 = max(0, layer_y)
            dst_x2 = min(self.width, layer_x + layer_w)
            dst_y2 = min(self.height, layer_y + layer_h)

            # Calculate source region
            src_x1 = dst_x1 - layer_x
            src_y1 = dst_y1 - layer_y
            src_x2 = src_x1 + (dst_x2 - dst_x1)
            src_y2 = src_y1 + (dst_y2 - dst_y1)

            # Skip if no visible region
            if dst_x2 <= dst_x1 or dst_y2 <= dst_y1:
                continue

            # Alpha blend
            src_region = frame_pixels[src_y1:src_y2, src_x1:src_x2]
            dst_region = canvas[dst_y1:dst_y2, dst_x1:dst_x2]

            # Calculate alpha for blending (normalized to 0-1)
            alpha = src_region[:, :, 3:4].astype(np.float32) / 255.0

            # Blend: dst = src * alpha + dst * (1 - alpha)
            blended = (
                src_region[:, :, :3].astype(np.float32) * alpha +
                dst_region[:, :, :3].astype(np.float32) * (1.0 - alpha)
            ).astype(np.uint8)

            # Update canvas
            canvas[dst_y1:dst_y2, dst_x1:dst_x2, :3] = blended
            # Combine alpha: dst_alpha = src_alpha + dst_alpha * (1 - src_alpha)
            canvas[dst_y1:dst_y2, dst_x1:dst_x2, 3] = (
                src_region[:, :, 3].astype(np.float32) +
                dst_region[:, :, 3].astype(np.float32) * (1.0 - alpha[:, :, 0])
            ).astype(np.uint8)

        return Image(canvas, pixel_format='RGBA')

    def composite_rgb(self, timestamp: float = 0.0) -> "Image":
        """Composite all layers and return as RGB (no alpha).

        :param timestamp: Current playback timestamp
        :return: Composited RGB Image
        """
        result = self.composite(timestamp)
        return result.convert('RGB')
