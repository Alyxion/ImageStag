# ImageStag Filters - Channel Operations
"""
Filters for splitting and merging image channels.

These filters enable working with individual color channels,
allowing per-channel processing in filter pipelines.
"""

from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

import numpy as np

from .base import Filter, FilterContext, FilterOutput, register_filter
from .graph import CombinerFilter
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
class SplitChannels(Filter):
    """Split RGB/RGBA image into individual channel images.

    Each output is a grayscale image with metadata['channel'] set to
    the channel name ('R', 'G', 'B', or 'A').

    Example:
        split = SplitChannels()
        result = split.apply(rgb_image)
        # result = {'R': gray_r, 'G': gray_g, 'B': gray_b}
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]
    _gallery_multi_output: ClassVar[bool] = True  # Show R/G/B as colored grid

    _output_ports: ClassVar[list[dict]] = [
        {'name': 'R', 'description': 'Red channel'},
        {'name': 'G', 'description': 'Green channel'},
        {'name': 'B', 'description': 'Blue channel'},
    ]

    def apply(
        self, image: 'Image', context: FilterContext | None = None
    ) -> FilterOutput:
        """Split image into channel images."""
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat

        channels = image.split()
        band_names = image.band_names

        result: dict[str, Image] = {}
        for data, name in zip(channels, band_names):
            # Create grayscale image from channel data
            ch_img = Img(data.astype(np.uint8), pixel_format=PixelFormat.GRAY)
            # Store channel origin in metadata
            ch_img.metadata['channel'] = name
            ch_img.metadata['source_format'] = image.pixel_format.name
            result[name] = ch_img

        return result


@register_filter
class MergeChannels(CombinerFilter):
    """Merge R, G, B grayscale channels back into an RGB image.

    Takes three grayscale images and combines them into RGB.

    Example:
        merge = MergeChannels(inputs=['R', 'G', 'B'])
        result = merge.apply_multi({'R': r_img, 'G': g_img, 'B': b_img})
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'R', 'description': 'Red channel'},
        {'name': 'G', 'description': 'Green channel'},
        {'name': 'B', 'description': 'Blue channel'},
    ]

    def apply_multi(
        self,
        images: dict[str, 'Image'],
        contexts: dict[str, FilterContext] | None = None,
    ) -> 'Image':
        """Merge channel images into RGB."""
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat

        # Get channels from inputs list or default order
        if self.inputs and len(self.inputs) >= 3:
            r_key, g_key, b_key = self.inputs[0], self.inputs[1], self.inputs[2]
        else:
            r_key, g_key, b_key = 'R', 'G', 'B'

        r = images[r_key].get_pixels_gray()
        g = images[g_key].get_pixels_gray()
        b = images[b_key].get_pixels_gray()

        # Stack channels into RGB
        rgb = np.stack([r, g, b], axis=2)
        return Img(rgb.astype(np.uint8), pixel_format=PixelFormat.RGB)


@register_filter
class ExtractChannel(Filter):
    """Extract a single channel from an image.

    Outputs a grayscale image with metadata['channel'] set.

    :param channel: Channel to extract ('R', 'G', 'B', 'A', or integer index)
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    channel: str = 'R'
    _primary_param: ClassVar[str | None] = 'channel'

    def apply(
        self, image: 'Image', context: FilterContext | None = None
    ) -> 'Image':
        """Extract specified channel."""
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat

        channels = image.split()
        band_names = image.band_names

        # Find channel by name or index
        if self.channel.isdigit():
            idx = int(self.channel)
            if idx >= len(channels):
                raise ValueError(f"Channel index {idx} out of range")
            data = channels[idx]
            name = band_names[idx] if idx < len(band_names) else str(idx)
        else:
            try:
                idx = band_names.index(self.channel.upper())
                data = channels[idx]
                name = self.channel.upper()
            except ValueError:
                raise ValueError(
                    f"Channel '{self.channel}' not found. "
                    f"Available: {band_names}"
                )

        result = Img(data.astype(np.uint8), pixel_format=PixelFormat.GRAY)
        result.metadata['channel'] = name
        result.metadata['source_format'] = image.pixel_format.name
        return result
