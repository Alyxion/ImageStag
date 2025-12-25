# ImageStag Filters - Analyzers
"""
Analyzer filters that extract information without modifying the image.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TYPE_CHECKING

import numpy as np

from .base import AnalyzerFilter, FilterContext, register_filter
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class ImageStats(AnalyzerFilter):
    """Compute basic image statistics.

    Results include per-channel mean, std, min, max, and overall brightness.

    Example:
        pipeline = FilterPipeline([
            ImageStats(result_key='stats'),
            Brightness(factor=1.5),
        ])
        ctx = FilterContext()
        result = pipeline.apply(image, ctx)
        print(ctx['stats']['brightness'])  # Average brightness
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    result_key: str = 'stats'

    def analyze(self, image: Image) -> dict[str, Any]:
        from imagestag.pixel_format import PixelFormat

        pixels = image.get_pixels(PixelFormat.RGB).astype(np.float32)

        stats = {
            'width': image.width,
            'height': image.height,
            'brightness': float(np.mean(pixels)),
            'channels': {},
        }

        channel_names = ['red', 'green', 'blue']
        for i, name in enumerate(channel_names):
            channel = pixels[:, :, i]
            stats['channels'][name] = {
                'mean': float(np.mean(channel)),
                'std': float(np.std(channel)),
                'min': float(np.min(channel)),
                'max': float(np.max(channel)),
            }

        return stats


@register_filter
@dataclass
class HistogramAnalyzer(AnalyzerFilter):
    """Compute image histogram.

    Results include per-channel histograms with 256 bins (0-255).

    Example:
        ctx = FilterContext()
        HistogramAnalyzer().apply(image, ctx)
        red_hist = ctx['histogram']['red']  # 256 values
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    result_key: str = 'histogram'
    bins: int = 256

    def analyze(self, image: Image) -> dict[str, list[int]]:
        from imagestag.pixel_format import PixelFormat

        pixels = image.get_pixels(PixelFormat.RGB)
        result = {}

        channel_names = ['red', 'green', 'blue']
        for i, name in enumerate(channel_names):
            channel = pixels[:, :, i].flatten()
            hist, _ = np.histogram(channel, bins=self.bins, range=(0, 255))
            result[name] = hist.tolist()

        # Also compute luminance histogram
        gray = 0.299 * pixels[:, :, 0] + 0.587 * pixels[:, :, 1] + 0.114 * pixels[:, :, 2]
        hist, _ = np.histogram(gray.flatten(), bins=self.bins, range=(0, 255))
        result['luminance'] = hist.tolist()

        return result


@register_filter
@dataclass
class ColorAnalyzer(AnalyzerFilter):
    """Analyze dominant colors in the image.

    Results include average color and basic color distribution.

    Example:
        ctx = FilterContext()
        ColorAnalyzer().apply(image, ctx)
        avg = ctx['colors']['average']  # (r, g, b) tuple
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    result_key: str = 'colors'

    def analyze(self, image: Image) -> dict[str, Any]:
        from imagestag.pixel_format import PixelFormat

        pixels = image.get_pixels(PixelFormat.RGB)

        # Average color
        avg_r = float(np.mean(pixels[:, :, 0]))
        avg_g = float(np.mean(pixels[:, :, 1]))
        avg_b = float(np.mean(pixels[:, :, 2]))

        # Color variance (measure of how colorful)
        r_var = float(np.var(pixels[:, :, 0]))
        g_var = float(np.var(pixels[:, :, 1]))
        b_var = float(np.var(pixels[:, :, 2]))

        # Saturation estimate (difference between max and min channels)
        max_channel = np.maximum(np.maximum(pixels[:, :, 0], pixels[:, :, 1]), pixels[:, :, 2])
        min_channel = np.minimum(np.minimum(pixels[:, :, 0], pixels[:, :, 1]), pixels[:, :, 2])
        saturation = float(np.mean(max_channel - min_channel))

        return {
            'average': (avg_r, avg_g, avg_b),
            'variance': (r_var, g_var, b_var),
            'saturation': saturation,
        }


@register_filter
@dataclass
class RegionAnalyzer(AnalyzerFilter):
    """Analyze a specific region of the image.

    Useful for checking specific areas (e.g., corners, center).

    Example:
        # Analyze center 50x50 region
        ctx = FilterContext()
        RegionAnalyzer(x=100, y=100, width=50, height=50).apply(image, ctx)
        print(ctx['region']['brightness'])
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    x: int = 0
    y: int = 0
    width: int = 0  # 0 = full width
    height: int = 0  # 0 = full height
    result_key: str = 'region'

    def analyze(self, image: Image) -> dict[str, Any]:
        from imagestag.pixel_format import PixelFormat

        # Determine region bounds
        x1 = max(0, self.x)
        y1 = max(0, self.y)
        x2 = min(image.width, x1 + (self.width or image.width))
        y2 = min(image.height, y1 + (self.height or image.height))

        pixels = image.get_pixels(PixelFormat.RGB)
        region = pixels[y1:y2, x1:x2]

        return {
            'bounds': (x1, y1, x2, y2),
            'size': (x2 - x1, y2 - y1),
            'brightness': float(np.mean(region)),
            'std': float(np.std(region)),
            'average_color': (
                float(np.mean(region[:, :, 0])),
                float(np.mean(region[:, :, 1])),
                float(np.mean(region[:, :, 2])),
            ),
        }


@register_filter
@dataclass
class BoundingBoxDetector(AnalyzerFilter):
    """Base class for object detection that returns bounding boxes.

    Subclass this to implement specific detectors (faces, objects, etc.).
    Results are stored as a list of detected regions.

    Each detection is a dict with:
        - box: (x, y, width, height)
        - confidence: float 0-1
        - label: str (optional)

    Example:
        @register_filter
        @dataclass
        class FaceDetector(BoundingBoxDetector):
            result_key: str = 'faces'

            def detect(self, image: Image) -> list[dict]:
                # Use OpenCV, dlib, or ML model here
                return [{'box': (10, 20, 50, 50), 'confidence': 0.95}]
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    result_key: str = 'detections'
    min_confidence: float = 0.5

    def analyze(self, image: Image) -> list[dict[str, Any]]:
        """Run detection and filter by confidence."""
        detections = self.detect(image)
        return [d for d in detections if d.get('confidence', 1.0) >= self.min_confidence]

    def detect(self, image: Image) -> list[dict[str, Any]]:
        """Override to implement actual detection.

        :returns: List of detections, each with 'box' and optionally 'confidence', 'label'.
        """
        return []  # Base implementation returns no detections
