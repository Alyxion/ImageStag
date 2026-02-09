# ImageStag Filters - Gradient Generator (Rust-backed)
"""
GradientGenerator filter for creating multi-stop gradient images.

Uses the Rust backend for high-performance gradient surface generation.
Supports 5 gradient styles: linear, radial, angle, reflected, diamond.
Separate scale_x/scale_y and offset_x/offset_y for full Affinity-style control.

For simple two-color gradients, see also ``ImageGenerator`` in ``generator.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, TYPE_CHECKING

import numpy as np

from .base import Filter, FilterContext, register_filter
from imagestag.pixel_format import PixelFormat
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image

try:
    import imagestag_rust
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


@register_filter
@dataclass
class GradientGenerator(Filter):
    """Generate multi-stop gradient surfaces using Rust backend.

    Creates gradient images with 5 style options and full control over
    scale, offset, and angle. Much faster than the pure-Python ImageGenerator
    for gradient generation.

    Parameters:
        style: Gradient style ("linear", "radial", "angle", "reflected", "diamond")
        angle: Angle in degrees (for linear/reflected styles)
        gradient: List of gradient stops [{"position": float, "color": "#RRGGBB"}, ...]
        scale_x: Horizontal scale factor (1.0 = 100%)
        scale_y: Vertical scale factor (1.0 = 100%)
        offset_x: Horizontal center offset (-1.0 to 1.0)
        offset_y: Vertical center offset (-1.0 to 1.0)
        reverse: Reverse gradient direction
        width: Output width (used when no input image)
        height: Output height (used when no input image)
        format: Output format ("rgb" or "rgba")

    Example:
        >>> from imagestag.filters.gradient_generator import GradientGenerator
        >>> gen = GradientGenerator(
        ...     style="radial",
        ...     gradient=[
        ...         {"position": 0.0, "color": "#FF0000"},
        ...         {"position": 0.5, "color": "#00FF00"},
        ...         {"position": 1.0, "color": "#0000FF"},
        ...     ],
        ...     width=256, height=256,
        ... )
        >>> result = gen.apply(None)
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW]

    style: str = "linear"
    angle: float = 90.0
    gradient: list = field(default_factory=lambda: [
        {"position": 0.0, "color": "#000000"},
        {"position": 1.0, "color": "#FFFFFF"},
    ])
    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    reverse: bool = False
    width: int = 512
    height: int = 512
    format: str = "rgba"

    def _gradient_to_flat_stops(self) -> list[float]:
        """Convert gradient stops to flat array [pos, r, g, b, ...] with 0-255 values."""
        flat = []
        for stop in self.gradient:
            pos = stop.get("position", 0.0)
            color = stop.get("color", "#000000").lstrip("#")
            if len(color) == 6:
                r = int(color[0:2], 16)
                g = int(color[2:4], 16)
                b = int(color[4:6], 16)
            else:
                r, g, b = 0, 0, 0
            flat.extend([float(pos), float(r), float(g), float(b)])
        return flat

    def apply(self, image: 'Image | None', context: FilterContext | None = None) -> 'Image':
        """Generate a gradient surface.

        Args:
            image: Optional input image (used for dimensions if provided).
                   Pass None to use width/height fields.
            context: Filter context (unused).

        Returns:
            Image with gradient surface.
        """
        from imagestag import Image

        if image is not None:
            w = image.width
            h = image.height
        else:
            w = self.width
            h = self.height

        channels = 4 if self.format == "rgba" else 3
        stops = self._gradient_to_flat_stops()

        if HAS_RUST:
            result_array = imagestag_rust.generate_gradient(
                w, h, stops,
                self.style,
                float(self.angle),
                float(self.scale_x),
                float(self.scale_y),
                float(self.offset_x),
                float(self.offset_y),
                bool(self.reverse),
                channels,
            )
        else:
            # Minimal pure-Python fallback (linear only)
            result_array = self._fallback_generate(w, h, channels)

        return Image(result_array)

    def _fallback_generate(self, w: int, h: int, channels: int) -> np.ndarray:
        """Pure Python fallback for linear gradient (no Rust)."""
        import math
        result = np.zeros((h, w, channels), dtype=np.uint8)
        angle_rad = math.radians(self.angle)
        dx = math.cos(angle_rad)
        dy = -math.sin(angle_rad)
        cx, cy = w / 2.0, h / 2.0
        max_dist = math.sqrt(cx**2 + cy**2)

        stops = sorted(self.gradient, key=lambda s: s.get("position", 0))
        if not stops:
            stops = [{"position": 0.0, "color": "#000000"}, {"position": 1.0, "color": "#FFFFFF"}]

        parsed = []
        for s in stops:
            color = s.get("color", "#000000").lstrip("#")
            r = int(color[0:2], 16) if len(color) >= 6 else 0
            g = int(color[2:4], 16) if len(color) >= 6 else 0
            b = int(color[4:6], 16) if len(color) >= 6 else 0
            parsed.append((s.get("position", 0.0), r, g, b))

        for y in range(h):
            for x in range(w):
                rx = (x - cx) / (self.scale_x or 1)
                ry = (y - cy) / (self.scale_y or 1)
                proj = rx * dx + ry * dy
                t = max(0.0, min(1.0, (proj / max_dist + 1.0) / 2.0))
                if self.reverse:
                    t = 1.0 - t

                # Interpolate
                prev = parsed[0]
                nxt = parsed[-1]
                for i, s in enumerate(parsed):
                    if s[0] <= t:
                        prev = s
                    if s[0] >= t and i > 0:
                        nxt = s
                        break

                if abs(nxt[0] - prev[0]) < 0.0001:
                    r, g, b = prev[1], prev[2], prev[3]
                else:
                    lt = max(0, min(1, (t - prev[0]) / (nxt[0] - prev[0])))
                    r = int(prev[1] + (nxt[1] - prev[1]) * lt)
                    g = int(prev[2] + (nxt[2] - prev[2]) * lt)
                    b = int(prev[3] + (nxt[3] - prev[3]) * lt)

                result[y, x, 0] = r
                result[y, x, 1] = g
                result[y, x, 2] = b
                if channels == 4:
                    result[y, x, 3] = 255

        return result
