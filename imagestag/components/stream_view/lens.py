"""Lens - Reusable picture-in-picture lens component for StreamView.

A Lens creates a movable window that shows a processed view of the content
beneath it. Common uses include:
- Thermal/false-color visualization
- Magnification/zoom lens
- Edge detection or other filter effects
- Picture-in-picture preview

Example:
    from imagestag.components.stream_view import StreamView, VideoStream, Lens
    from imagestag.filters import FalseColor

    view = StreamView(width=960, height=540)
    video = VideoStream('video.mp4')
    view.add_layer(stream=video, fps=60)

    # Create a thermal lens
    thermal_lens = Lens(
        view=view,
        video_layer=video_layer,
        width=200,
        height=150,
        filter_fn=lambda img: FalseColor('hot').apply(img),
        overscan=16,
    )

    # Attach to video stream for automatic updates
    thermal_lens.attach(video_stream)

    # In mouse handler:
    @view.on_mouse_move
    def on_mouse(e):
        thermal_lens.move_to(e.x, e.y)
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

import numpy as np

if TYPE_CHECKING:
    from imagestag import Image
    from .layers import StreamViewLayer, VideoStream
    from .stream_view import StreamView


@dataclass
class Lens:
    """A movable lens that shows processed content from beneath it.

    The lens automatically handles:
    - Edge-aware cropping with black padding
    - Overscan for smooth movement
    - Viewport/zoom tracking
    - Frame injection into StreamView layer
    - Optional alpha masking for smooth circular/elliptical edges

    Attributes:
        view: The StreamView this lens belongs to
        video_layer: The layer to read viewport state from (for zoom/pan)
        width: Display width of the lens in pixels
        height: Display height of the lens in pixels
        filter_fn: Function to apply to cropped region (Image -> Image)
        overscan: Extra pixels on each side for smooth movement
        z_index: Stacking order (higher = on top)
        jpeg_quality: JPEG encoding quality (1-100)
        initial_x: Initial X position
        initial_y: Initial Y position
        mask_shape: Shape of alpha mask ("circle", "ellipse", "rounded_rect", None)
        mask_feather: Feather/fade width at edges in pixels (0 = hard edge)
        mask_corner_radius: Corner radius for "rounded_rect" shape
    """

    view: "StreamView"
    video_layer: "StreamViewLayer | None"  # None for WebRTC mode (uses view's viewport)
    width: int = 200
    height: int = 150
    filter_fn: Callable[["Image"], "Image"] | None = None
    overscan: int = 16
    z_index: int = 15
    jpeg_quality: int = 80
    initial_x: int | None = None
    initial_y: int | None = None
    name: str = ""  # Display name for metrics overlay
    mask_shape: str | None = None  # "circle", "ellipse", "rounded_rect", or None
    mask_feather: int = 8  # Feather width in pixels
    mask_corner_radius: int = 20  # For rounded_rect shape

    # Runtime state
    _layer: "StreamViewLayer" = field(default=None, init=False, repr=False)
    _attached_stream: "VideoStream" = field(default=None, init=False, repr=False)
    _alpha_mask: np.ndarray = field(default=None, init=False, repr=False)
    _mask_sent: bool = field(default=False, init=False, repr=False)

    @property
    def _display_w(self) -> int:
        """Current display width (from view)."""
        return self.view._width

    @property
    def _display_h(self) -> int:
        """Current display height (from view)."""
        return self.view._height

    def __post_init__(self) -> None:
        """Initialize the lens and create its layer."""
        # Default position: top-right corner
        if self.initial_x is None:
            self.initial_x = self.view._width - self.width - 10
        if self.initial_y is None:
            self.initial_y = 10

        # Generate alpha mask if shape is specified
        if self.mask_shape is not None:
            self._alpha_mask = self._generate_alpha_mask()

        # Create the layer for this lens (always JPEG, mask sent separately)
        self._layer = self.view.add_layer(
            name=self.name,  # User-friendly name for metrics
            piggyback=True,
            fps=60,
            z_index=self.z_index,
            buffer_size=1,
            jpeg_quality=self.jpeg_quality,
            use_png=False,  # Always JPEG - mask is sent separately
            depth=0.0,  # Fixed overlay
            x=self.initial_x,
            y=self.initial_y,
            width=self.width,
            height=self.height,
            overscan=self.overscan,
        )

    def _generate_alpha_mask(self) -> np.ndarray:
        """Generate an alpha mask for the lens shape.

        The mask is sized to the visible lens area (width x height) and positioned
        to clip the overscan region, hiding any black edges from edge cropping.

        :return: Alpha mask as uint8 array (H+2*overscan, W+2*overscan)
        """
        # Full dimensions including overscan
        full_w = self.width + 2 * self.overscan
        full_h = self.height + 2 * self.overscan

        # The visible lens area (without overscan)
        vis_w = self.width
        vis_h = self.height

        # Center of the full area
        cx, cy = full_w / 2, full_h / 2

        # Create coordinate grids
        y_coords, x_coords = np.mgrid[0:full_h, 0:full_w].astype(np.float32)

        # Extra inset to ensure we clip any black edge artifacts
        edge_margin = 2

        if self.mask_shape == "circle":
            # Use the smaller visible dimension for a perfect circle
            radius = min(vis_w, vis_h) / 2 - self.mask_feather - edge_margin
            dist = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2)
            # Alpha = 1 inside, fade to 0 at edge
            alpha = np.clip((radius + self.mask_feather - dist) / max(1, self.mask_feather), 0, 1)

        elif self.mask_shape == "ellipse":
            # Ellipse sized to visible area
            rx = vis_w / 2 - self.mask_feather - edge_margin
            ry = vis_h / 2 - self.mask_feather - edge_margin
            # Normalized distance from center (1.0 = on ellipse edge)
            dist = np.sqrt(((x_coords - cx) / max(1, rx)) ** 2 + ((y_coords - cy) / max(1, ry)) ** 2)
            # Feather in normalized space
            feather_norm = self.mask_feather / max(1, min(rx, ry))
            alpha = np.clip((1 + feather_norm - dist) / max(0.01, feather_norm), 0, 1)

        elif self.mask_shape == "rounded_rect":
            # Rounded rectangle sized to visible area
            r = self.mask_corner_radius
            feather = self.mask_feather

            # Calculate inner rect bounds (visible area within full area)
            inner_left = self.overscan + edge_margin
            inner_right = full_w - self.overscan - edge_margin
            inner_top = self.overscan + edge_margin
            inner_bottom = full_h - self.overscan - edge_margin

            # Distance from inner rect edges
            dx = np.maximum(0, np.maximum(inner_left + r - x_coords, x_coords - (inner_right - r)))
            dy = np.maximum(0, np.maximum(inner_top + r - y_coords, y_coords - (inner_bottom - r)))

            # In corner regions, use circular distance
            corner_dist = np.sqrt(dx ** 2 + dy ** 2) - r

            # Edge distance (negative = inside, positive = outside)
            edge_dist_x = np.maximum(inner_left + feather - x_coords, x_coords - (inner_right - feather))
            edge_dist_y = np.maximum(inner_top + feather - y_coords, y_coords - (inner_bottom - feather))

            # Combine: use corner distance in corners, edge distance elsewhere
            in_corner = (dx > 0) & (dy > 0)
            dist = np.where(in_corner, corner_dist, np.maximum(edge_dist_x, edge_dist_y))

            alpha = np.clip((feather - dist) / max(1, feather), 0, 1)

        else:
            # No mask (full opacity)
            alpha = np.ones((full_h, full_w), dtype=np.float32)

        return (alpha * 255).astype(np.uint8)

    def _send_mask_to_client(self, content_width: int, content_height: int) -> None:
        """Send the alpha mask to the client for client-side compositing.

        The mask is sent once as a PNG and cached on the client.
        Client uses it with globalCompositeOperation to apply the alpha.

        :param content_width: Width of the content frames
        :param content_height: Height of the content frames
        """
        from imagestag import Image
        import cv2

        mask = self._alpha_mask

        # Resize mask if dimensions don't match
        if mask.shape[0] != content_height or mask.shape[1] != content_width:
            mask = cv2.resize(
                mask,
                (content_width, content_height),
                interpolation=cv2.INTER_LINEAR,
            )

        # Create grayscale PNG (single channel alpha)
        # Client will use this as a mask
        png_bytes = Image(mask, pixel_format="GRAY").to_png()
        mask_data = f"data:image/png;base64,{base64.b64encode(png_bytes).decode('ascii')}"

        # Send mask to client via StreamView
        self.view.run_method("setLayerMask", self._layer.id, mask_data)
        self._mask_sent = True

    @property
    def layer(self) -> "StreamViewLayer":
        """The StreamView layer for this lens."""
        return self._layer

    @property
    def id(self) -> str:
        """Layer ID for this lens."""
        return self._layer.id

    @property
    def x(self) -> int:
        """Current X position."""
        return self._layer.x or 0

    @property
    def y(self) -> int:
        """Current Y position."""
        return self._layer.y or 0

    def move_to(self, x: int, y: int, center: bool = True) -> None:
        """Move the lens to a position.

        :param x: Target X coordinate
        :param y: Target Y coordinate
        :param center: If True, center lens on (x, y); if False, use as top-left
        """
        if center:
            lens_x = x - self.width // 2
            lens_y = y - self.height // 2
        else:
            lens_x = x
            lens_y = y

        # Allow lens to go partially off-screen (keep at least 20px visible)
        min_visible = 20
        lens_x = max(-self.width + min_visible, min(lens_x, self._display_w - min_visible))
        lens_y = max(-self.height + min_visible, min(lens_y, self._display_h - min_visible))

        self.view.update_layer_position(self._layer.id, x=lens_x, y=lens_y)

    def attach(self, video_stream: "VideoStream") -> None:
        """Attach to a video stream for automatic frame updates.

        When attached, the lens will automatically update whenever
        the video stream captures a new frame.

        :param video_stream: The video stream to attach to
        """
        self._attached_stream = video_stream
        video_stream.on_frame(self._on_frame)

    def detach(self) -> None:
        """Detach from the video stream."""
        if self._attached_stream is not None:
            self._attached_stream.remove_on_frame(self._on_frame)
            self._attached_stream = None

    def update(self, frame: "Image", capture_time: float | None = None) -> None:
        """Manually update the lens with a frame.

        Use this when not attached to a video stream, or for
        custom update logic.

        :param frame: The source frame to crop and process
        :param capture_time: Optional capture timestamp (defaults to now)
        """
        if capture_time is None:
            capture_time = time.perf_counter()
        self._process_frame(frame, capture_time)

    def _on_frame(self, frame: "Image", capture_time: float) -> None:
        """Callback for video stream frame events."""
        self._process_frame(frame, capture_time)

    def _process_frame(self, frame: "Image", capture_time: float) -> None:
        """Process a frame and inject into the layer."""
        from imagestag import Image

        t0 = time.perf_counter()

        # Get viewport state from video layer or StreamView (for WebRTC mode)
        if self.video_layer is not None:
            zoom = self.video_layer._viewport_zoom
            vp_x = self.video_layer._viewport_x
            vp_y = self.video_layer._viewport_y
        else:
            # Fallback to StreamView's viewport (WebRTC mode)
            zoom = self.view._viewport.zoom
            vp_x = self.view._viewport.x
            vp_y = self.view._viewport.y

        # Get lens position
        lens_x = self._layer.x or 0
        lens_y = self._layer.y or 0

        # Calculate lens center in display coords
        lens_center_x = lens_x + self.width // 2
        lens_center_y = lens_y + self.height // 2

        # Convert to normalized coords (0-1)
        norm_x = lens_center_x / self._display_w
        norm_y = lens_center_y / self._display_h

        # Convert to source coords accounting for viewport
        source_norm_x = vp_x + norm_x / zoom
        source_norm_y = vp_y + norm_y / zoom

        # Scale to pixel coordinates in source frame
        cx = int(source_norm_x * frame.width)
        cy = int(source_norm_y * frame.height)

        # Calculate crop size with overscan
        display_w_with_overscan = self.width + 2 * self.overscan
        display_h_with_overscan = self.height + 2 * self.overscan
        crop_w = int(display_w_with_overscan * frame.width / self._display_w / zoom)
        crop_h = int(display_h_with_overscan * frame.height / self._display_h / zoom)

        # Calculate ideal crop region
        ideal_x1 = cx - crop_w // 2
        ideal_y1 = cy - crop_h // 2
        ideal_x2 = ideal_x1 + crop_w
        ideal_y2 = ideal_y1 + crop_h

        # Get frame data as numpy array
        frame_data = frame.get_pixels_rgb()

        # Create black canvas of desired crop size
        canvas = np.zeros((max(1, crop_h), max(1, crop_w), 3), dtype=np.uint8)

        # Calculate source region (clamped to frame bounds)
        src_x1 = max(0, ideal_x1)
        src_y1 = max(0, ideal_y1)
        src_x2 = min(frame.width, ideal_x2)
        src_y2 = min(frame.height, ideal_y2)

        # Calculate destination region in canvas
        dst_x1 = src_x1 - ideal_x1
        dst_y1 = src_y1 - ideal_y1
        dst_x2 = dst_x1 + (src_x2 - src_x1)
        dst_y2 = dst_y1 + (src_y2 - src_y1)

        # Copy valid region if there is overlap
        if src_x2 > src_x1 and src_y2 > src_y1:
            canvas[dst_y1:dst_y2, dst_x1:dst_x2] = frame_data[src_y1:src_y2, src_x1:src_x2]

        cropped = Image(canvas, pixel_format="RGB")
        t_crop = time.perf_counter()

        # Apply filter if provided
        if self.filter_fn is not None:
            cropped = self.filter_fn(cropped)
        t_filter = time.perf_counter()

        # Send mask to client once (if we have one and haven't sent it yet)
        if self._alpha_mask is not None and not self._mask_sent:
            self._send_mask_to_client(cropped.width, cropped.height)

        # Always encode to JPEG (mask is applied client-side)
        jpeg_bytes = cropped.to_jpeg(quality=self.jpeg_quality)
        encoded = f"data:image/jpeg;base64,{base64.b64encode(jpeg_bytes).decode('ascii')}"
        t_encode = time.perf_counter()

        # Inject into layer
        self._layer.inject_frame(
            encoded=encoded,
            birth_time=capture_time,
            step_timings={
                'crop_ms': (t_crop - t0) * 1000,
                'filter_ms': (t_filter - t_crop) * 1000,
                'enc_ms': (t_encode - t_filter) * 1000,
            },
            anchor_x=lens_x,
            anchor_y=lens_y,
        )

    def update_from_last_frame(self) -> None:
        """Update the lens using the last frame from attached stream.

        Useful for updating the lens when video is paused but
        the lens position has changed.
        """
        if self._attached_stream is not None:
            last_frame = self._attached_stream.last_frame
            if last_frame is not None:
                self.update(last_frame)


def create_zoom_lens(
    view: "StreamView",
    video_layer: "StreamViewLayer | None",
    zoom_factor: float = 2.0,
    width: int = 200,
    height: int = 150,
    mask_shape: str | None = None,
    mask_feather: int = 8,
    **kwargs,
) -> Lens:
    """Create a magnifying lens that shows a zoomed view.

    :param view: The StreamView
    :param video_layer: The video layer to track viewport from
    :param zoom_factor: Magnification factor (2.0 = 2x zoom)
    :param width: Lens width in pixels
    :param height: Lens height in pixels
    :param mask_shape: Shape of alpha mask ("circle", "ellipse", "rounded_rect", None)
    :param mask_feather: Feather/fade width at edges in pixels
    :param kwargs: Additional arguments passed to Lens
    :return: Configured Lens instance
    """
    from imagestag import Image

    def zoom_filter(img: Image) -> Image:
        # Calculate center crop for zoom effect
        src_w, src_h = img.width, img.height
        crop_w = int(src_w / zoom_factor)
        crop_h = int(src_h / zoom_factor)
        x1 = (src_w - crop_w) // 2
        y1 = (src_h - crop_h) // 2

        # Crop center and resize back to original size
        cropped = img.cropped((x1, y1, x1 + crop_w - 1, y1 + crop_h - 1))
        return cropped.resized((src_w, src_h))

    return Lens(
        view=view,
        video_layer=video_layer,
        width=width,
        height=height,
        filter_fn=zoom_filter,
        mask_shape=mask_shape,
        mask_feather=mask_feather,
        **kwargs,
    )


def create_thermal_lens(
    view: "StreamView",
    video_layer: "StreamViewLayer | None",
    colormap: str = "hot",
    width: int = 200,
    height: int = 150,
    mask_shape: str | None = "ellipse",
    mask_feather: int = 12,
    **kwargs,
) -> Lens:
    """Create a thermal/false-color lens.

    :param view: The StreamView
    :param video_layer: The video layer to track viewport from
    :param colormap: Colormap name ('hot', 'jet', 'viridis', etc.)
    :param width: Lens width in pixels
    :param height: Lens height in pixels
    :param mask_shape: Shape of alpha mask ("circle", "ellipse", "rounded_rect", None)
    :param mask_feather: Feather/fade width at edges in pixels
    :param kwargs: Additional arguments passed to Lens
    :return: Configured Lens instance
    """
    from imagestag.filters import FalseColor

    false_color = FalseColor(colormap=colormap)

    return Lens(
        view=view,
        video_layer=video_layer,
        width=width,
        height=height,
        filter_fn=false_color.apply,
        mask_shape=mask_shape,
        mask_feather=mask_feather,
        **kwargs,
    )


def create_magnifier_lens(
    view: "StreamView",
    video_layer: "StreamViewLayer | None",
    zoom_factor: float = 2.0,
    barrel_strength: float = 0.3,
    width: int = 200,
    height: int = 150,
    mask_shape: str | None = "circle",
    mask_feather: int = 15,
    **kwargs,
) -> Lens:
    """Create a magnifying glass lens with optional barrel distortion.

    Creates a lens that shows a zoomed, optionally curved view like
    looking through a magnifying glass.

    :param view: The StreamView
    :param video_layer: The video layer to track viewport from
    :param zoom_factor: Magnification factor (2.0 = 2x zoom)
    :param barrel_strength: Barrel distortion strength (0 = none, 0.5 = strong)
    :param width: Lens width in pixels
    :param height: Lens height in pixels
    :param mask_shape: Shape of alpha mask ("circle", "ellipse", "rounded_rect", None)
    :param mask_feather: Feather/fade width at edges in pixels
    :param kwargs: Additional arguments passed to Lens
    :return: Configured Lens instance
    """
    from imagestag import Image
    import cv2

    def magnifier_filter(img: Image) -> Image:
        src_w, src_h = img.width, img.height

        # First apply zoom by cropping center
        crop_w = int(src_w / zoom_factor)
        crop_h = int(src_h / zoom_factor)
        x1 = (src_w - crop_w) // 2
        y1 = (src_h - crop_h) // 2

        # Crop center
        data = img.get_pixels_rgb()
        cropped = data[y1:y1 + crop_h, x1:x1 + crop_w]

        # Resize back to original size
        zoomed = cv2.resize(cropped, (src_w, src_h), interpolation=cv2.INTER_LINEAR)

        # Apply barrel distortion if strength > 0
        if barrel_strength > 0:
            zoomed = _apply_barrel_distortion(zoomed, barrel_strength)

        return Image(zoomed, pixel_format="RGB")

    return Lens(
        view=view,
        video_layer=video_layer,
        width=width,
        height=height,
        filter_fn=magnifier_filter,
        mask_shape=mask_shape,
        mask_feather=mask_feather,
        **kwargs,
    )


def _apply_barrel_distortion(img: np.ndarray, strength: float) -> np.ndarray:
    """Apply barrel distortion effect to an image.

    :param img: Input image as numpy array (H, W, C)
    :param strength: Distortion strength (0 = none, 0.5 = strong curve)
    :return: Distorted image
    """
    import cv2

    h, w = img.shape[:2]
    cx, cy = w / 2, h / 2

    # Create coordinate grids
    y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)

    # Normalize coordinates to [-1, 1]
    x_norm = (x_coords - cx) / cx
    y_norm = (y_coords - cy) / cy

    # Calculate radius from center
    r = np.sqrt(x_norm**2 + y_norm**2)

    # Apply barrel distortion: r' = r * (1 + k * r^2)
    # This makes the center bulge out
    r_distorted = r * (1 + strength * r**2)

    # Avoid division by zero
    mask = r > 0.0001
    scale = np.ones_like(r)
    scale[mask] = r_distorted[mask] / r[mask]

    # Apply distortion to coordinates
    x_distorted = x_norm * scale
    y_distorted = y_norm * scale

    # Convert back to pixel coordinates
    map_x = (x_distorted * cx + cx).astype(np.float32)
    map_y = (y_distorted * cy + cy).astype(np.float32)

    # Remap the image
    result = cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

    return result
