# ImageStag Filters - Pipeline
"""
FilterPipeline for chaining multiple filters.

Supports automatic format conversion between filters, including:
- Pixel format conversion (RGB, BGR, RGBA, GRAY, etc.)
- Compressed format handling (JPEG, PNG bytes)
- Numpy array formats for OpenCV integration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
import re

from .base import Filter, FilterContext, register_filter
from .formats import FormatSpec, ImageData, Compression

if TYPE_CHECKING:
    from imagestag import Image


def _get_image_format(image: 'Image') -> FormatSpec:
    """Get the FormatSpec for an Image based on its pixel format."""
    from imagestag.pixel_format import PixelFormat

    pf_map = {
        PixelFormat.RGB: 'RGB',
        PixelFormat.RGBA: 'RGBA',
        PixelFormat.BGR: 'BGR',
        PixelFormat.BGRA: 'BGRA',
        PixelFormat.GRAY: 'GRAY',
        PixelFormat.HSV: 'HSV',
    }
    pf_str = pf_map.get(image.pixel_format, 'RGB')
    return FormatSpec(pixel_format=pf_str)


def _convert_image_format(image: 'Image', target_format: FormatSpec) -> 'Image':
    """Convert an Image to a target format."""
    from imagestag import Image as ImageClass
    from imagestag.pixel_format import PixelFormat
    import numpy as np

    if target_format._any:
        return image  # Any format accepted

    if target_format.pixel_format is None:
        return image  # No specific format required

    pf_map = {
        'RGB': PixelFormat.RGB,
        'RGBA': PixelFormat.RGBA,
        'BGR': PixelFormat.BGR,
        'BGRA': PixelFormat.BGRA,
        'GRAY': PixelFormat.GRAY,
        'HSV': PixelFormat.HSV,
    }

    target_pf = pf_map.get(target_format.pixel_format)
    if target_pf is None or target_pf == image.pixel_format:
        return image  # Already in the right format or unknown format

    # Handle BGR/BGRA conversion manually since PIL doesn't support it
    # Must use CV framework to keep BGR format
    from imagestag import ImsFramework

    if target_pf == PixelFormat.BGR:
        # Get RGB pixels and swap channels
        pixels = image.get_pixels(PixelFormat.RGB)
        bgr = pixels[:, :, ::-1].copy()
        return ImageClass(bgr, pixel_format=PixelFormat.BGR, framework=ImsFramework.CV)

    if target_pf == PixelFormat.BGRA:
        # Get RGBA pixels and swap RGB channels
        if image.pixel_format == PixelFormat.BGRA:
            return image
        pixels = image.get_pixels(PixelFormat.RGBA)
        bgra = np.empty_like(pixels)
        bgra[:, :, 0] = pixels[:, :, 2]  # B <- R
        bgra[:, :, 1] = pixels[:, :, 1]  # G <- G
        bgra[:, :, 2] = pixels[:, :, 0]  # R <- B
        bgra[:, :, 3] = pixels[:, :, 3]  # A <- A
        return ImageClass(bgra, pixel_format=PixelFormat.BGRA, framework=ImsFramework.CV)

    # For other formats, use built-in conversion
    return image.convert(target_pf)


def _convert_imagedata_format(data: ImageData, target_format: FormatSpec) -> ImageData:
    """Convert ImageData to a target format.

    Handles conversion between:
    - Pixel formats (RGB, BGR, RGBA, etc.)
    - Compressed formats (JPEG, PNG bytes)
    - Any combination
    """
    current_format = data.format

    # Check if already compatible
    if target_format._any or current_format.matches(target_format):
        return data

    # Handle compressed target formats
    if target_format.is_compressed():
        return ImageData.from_bytes(
            data.to_bytes(target_format.compression),
            compression=target_format.compression,
        )

    # Handle uncompressed target formats
    # Convert to array with the right pixel format
    array = data.to_array(
        pixel_format=target_format.pixel_format or 'RGB',
        bit_depth=target_format.bit_depth,
    )
    return ImageData.from_array(
        array,
        pixel_format=target_format.pixel_format or 'RGB',
        bit_depth=target_format.bit_depth,
    )


@register_filter
@dataclass
class FilterPipeline(Filter):
    """Chain of filters applied in sequence.

    Supports automatic format conversion between filters when a filter declares
    specific input format requirements and implicit_conversion is enabled.

    Can process:
    - Image objects (via apply())
    - ImageData containers (via process())
    - Any format that ImageData supports (JPEG bytes, numpy arrays, etc.)
    """
    filters: list[Filter] = field(default_factory=list)
    auto_convert: bool = True  # Enable automatic format conversion

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        """Apply all filters in sequence, with automatic format conversion.

        If auto_convert is enabled and a filter has format requirements,
        the image is automatically converted to a compatible format.
        """
        result = image
        for f in self.filters:
            # Check if format conversion is needed
            if self.auto_convert and f.accepts_implicit_conversion():
                accepted = f.get_accepted_formats()
                if accepted is not None:
                    current_format = _get_image_format(result)
                    if not f.accepts_format(current_format):
                        # Convert to first accepted format
                        result = _convert_image_format(result, accepted[0])

            result = f.apply(result, context)
        return result

    def process(self, data: ImageData, context: FilterContext | None = None) -> ImageData:
        """Process ImageData through all filters in sequence.

        Uses the universal ImageData format to support:
        - Compressed bytes (JPEG, PNG) as input/output
        - Numpy arrays with any pixel format
        - Image objects

        Automatic format conversion happens between filters when needed.

        :param data: Input data in any supported format.
        :param context: Optional context for storing/retrieving data.
        :returns: Processed data (format depends on last filter's output format).
        """
        result = data
        for f in self.filters:
            # Check if format conversion is needed
            if self.auto_convert and f.accepts_implicit_conversion():
                accepted = f.get_accepted_formats()
                if accepted is not None and not f.accepts_format(result.format):
                    # Convert to first accepted format
                    result = _convert_imagedata_format(result, accepted[0])

            result = f.process(result, context)

            # Apply output format if filter declares one
            output_format = f.get_output_format()
            if output_format is not None and not result.format.matches(output_format):
                result = _convert_imagedata_format(result, output_format)

        return result

    def append(self, filter: Filter) -> 'FilterPipeline':
        """Add filter to pipeline (chainable)."""
        self.filters.append(filter)
        return self

    def extend(self, filters: list[Filter]) -> 'FilterPipeline':
        """Add multiple filters to pipeline (chainable)."""
        self.filters.extend(filters)
        return self

    def __len__(self) -> int:
        return len(self.filters)

    def __iter__(self):
        return iter(self.filters)

    def __getitem__(self, index: int) -> Filter:
        return self.filters[index]

    def to_dict(self) -> dict[str, Any]:
        """Serialize pipeline to dictionary."""
        return {
            'type': 'FilterPipeline',
            'filters': [f.to_dict() for f in self.filters]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'FilterPipeline':
        """Deserialize pipeline from dictionary."""
        filters = [Filter.from_dict(f) for f in data.get('filters', [])]
        return cls(filters=filters)

    @classmethod
    def parse(cls, text: str) -> 'FilterPipeline':
        """Parse filter string into pipeline.

        Examples:
            'resize(0.5)|blur(1.5)|brightness(1.1)'
            'resize(scale=0.5);blur(radius=1.5)'
        """
        if not text:
            return cls()

        filters = []
        # Split by | or ;
        for part in re.split(r'[|;]', text):
            part = part.strip()
            if not part:
                continue
            filters.append(Filter.parse(part))

        return cls(filters=filters)

    def to_string(self) -> str:
        """Convert pipeline to compact string format."""
        return '|'.join(f.to_string() for f in self.filters)
