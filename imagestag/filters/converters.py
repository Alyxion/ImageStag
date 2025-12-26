# ImageStag Filters - Format Converters
"""
Filters for converting between image formats.

These filters convert between:
- Compressed formats (JPEG, PNG, WebP, BMP, GIF bytes)
- Pixel formats (RGB, BGR, GRAY, etc.)
- Array formats for OpenCV integration
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from .base import Filter, FilterContext, register_filter
from .formats import FormatSpec, ImageData, Compression
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class Encode(Filter):
    """Encode image to compressed bytes.

    Supports all standard image formats: JPEG, PNG, WebP, BMP, GIF.
    The result is an Image with compressed data that can be efficiently
    transported through pipelines without re-encoding.

    Parameters:
        format: Output format ('jpeg', 'png', 'webp', 'bmp', 'gif')
        quality: Compression quality 1-100 (for JPEG/WebP, default 90)

    Examples:
        Encode(format='jpeg', quality=85)
        Encode(format='png')

        # In pipeline string:
        'resize(0.5)|encode(format=jpeg,quality=85)'
        'blur(1.5)|encode(format=png)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    format: str = 'jpeg'
    quality: int = 90

    _primary_param: ClassVar[str] = 'format'
    _native_imagedata: ClassVar[bool] = True

    def __post_init__(self):
        # Normalize format name
        self.format = self.format.lower()
        if self.format == 'jpg':
            self.format = 'jpeg'

    def get_output_format(self) -> FormatSpec:
        """Get output format based on instance parameters."""
        compression = Compression.from_extension(self.format)
        return FormatSpec(compression=compression)

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        """Encode image to compressed bytes and return as compressed Image."""
        # Encode to bytes
        encoded_bytes = image.encode(self.format, quality=self.quality)
        # Return as compressed Image (lazy decode on pixel access)
        return image.from_compressed(encoded_bytes, f'image/{self.format}')

    def process(self, data: ImageData, context: FilterContext | None = None) -> ImageData:
        """Convert to compressed bytes."""
        compression = Compression.from_extension(self.format)
        encoded_bytes = data.to_bytes(compression, quality=self.quality)
        return ImageData.from_bytes(encoded_bytes, compression=compression)


@register_filter
@dataclass
class Decode(Filter):
    """Decode compressed bytes to uncompressed pixel data.

    Accepts any compressed format (JPEG, PNG, WebP, etc.) and outputs
    uncompressed image data in the specified pixel format. Forces
    decompression of compressed Image objects.

    Parameters:
        format: Output pixel format ('RGB', 'BGR', 'RGBA', 'GRAY')

    Examples:
        Decode(format='RGB')
        Decode(format='BGR')  # For OpenCV

        # In pipeline string:
        'encode(jpeg)|decode(RGB)'  # Encode then decode
        'decode(format=BGR)|some_cv_filter'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL, ImsFramework.RAW]

    format: str = 'RGB'

    _primary_param: ClassVar[str] = 'format'
    _accepted_formats: ClassVar[list[FormatSpec]] = [
        FormatSpec.JPEG, FormatSpec.PNG, FormatSpec(compression=Compression.WEBP),
        FormatSpec(compression=Compression.BMP), FormatSpec(compression=Compression.GIF),
    ]
    _native_imagedata: ClassVar[bool] = True

    def get_output_format(self) -> FormatSpec:
        """Get output format based on instance parameters."""
        return FormatSpec(pixel_format=self.format.upper())

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        """Decode compressed image and convert to specified pixel format."""
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat

        pf_map = {
            'RGB': PixelFormat.RGB,
            'RGBA': PixelFormat.RGBA,
            'BGR': PixelFormat.BGR,
            'BGRA': PixelFormat.BGRA,
            'GRAY': PixelFormat.GRAY,
        }
        target_format = pf_map.get(self.format.upper(), PixelFormat.RGB)

        # Force decode by accessing pixels
        pixels = image.get_pixels(target_format)

        # Return new uncompressed Image
        return Img(pixels, pixel_format=target_format)

    def process(self, data: ImageData, context: FilterContext | None = None) -> ImageData:
        """Decode to uncompressed format."""
        pf = self.format.upper()
        array = data.to_array(pixel_format=pf)
        return ImageData.from_array(array, pixel_format=pf)


@register_filter
@dataclass
class ToDataUrl(Filter):
    """Convert compressed image to base64 data URL.

    Takes a compressed image (from Encode filter) and produces a data URL
    string suitable for web display. This is the final step in pipelines
    that need web-ready output.

    The result is an Image with the data URL stored, accessible via
    `result.to_data_url()` which returns the cached URL without re-encoding.

    Parameters:
        format: Output format ('jpeg', 'png', 'webp') - uses existing if compressed
        quality: Compression quality 1-100 (only used if re-encoding needed)

    Examples:
        ToDataUrl()  # Use existing compression
        ToDataUrl(format='jpeg', quality=85)

        # In pipeline string:
        'resize(0.5)|encode(jpeg)|todataurl'
        'falsecolor(hot)|encode(png)|todataurl'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL, ImsFramework.RAW]
    _native_imagedata: ClassVar[bool] = True

    format: str = 'jpeg'
    quality: int = 85

    def __post_init__(self):
        self.format = self.format.lower()
        if self.format == 'jpg':
            self.format = 'jpeg'

    def get_output_format(self) -> FormatSpec:
        """Output is compressed with data URL available."""
        compression = Compression.from_extension(self.format)
        return FormatSpec(compression=compression)

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        """Convert image to data URL and store it."""
        import base64

        # Check if already compressed
        if image.is_compressed():
            # Use existing compressed data
            data = image._compressed_data
            mime = image._compressed_mime
        else:
            # Encode first
            data = image.encode(self.format, quality=self.quality)
            mime = f'image/{self.format}'

        # Encode to base64
        encoded = base64.b64encode(data).decode('ascii')
        data_url = f"data:{mime};base64,{encoded}"

        # Return compressed image with data URL cached in metadata
        result = image.from_compressed(data, mime)
        result.metadata['_data_url'] = data_url
        return result

    def process(self, data: ImageData, context: FilterContext | None = None) -> ImageData:
        """Convert ImageData to include data URL."""
        data_url = data.to_data_url(self.format, self.quality)
        return data.with_data_url(data_url)


@register_filter
@dataclass
class ConvertFormat(Filter):
    """Convert image to a specific pixel format.

    Useful for ensuring a specific format for downstream processing.

    Parameters:
        format: Target pixel format ('RGB', 'BGR', 'RGBA', 'BGRA', 'GRAY', 'HSV')

    Examples:
        ConvertFormat(format='BGR')  # For OpenCV
        ConvertFormat(format='GRAY')

        # In pipeline string:
        'convertformat(format=BGR)|blur(1.5)'
        'convertformat(BGR)'  # Short form
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]
    _supports_inplace: ClassVar[bool] = True

    format: str = 'RGB'

    _primary_param: ClassVar[str] = 'format'
    _native_imagedata: ClassVar[bool] = True

    def get_output_format(self) -> FormatSpec:
        """Get output format based on instance parameters."""
        return FormatSpec(pixel_format=self.format.upper())

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag.pixel_format import PixelFormat
        pf_map = {
            'RGB': PixelFormat.RGB,
            'RGBA': PixelFormat.RGBA,
            'BGR': PixelFormat.BGR,
            'BGRA': PixelFormat.BGRA,
            'GRAY': PixelFormat.GRAY,
            'HSV': PixelFormat.HSV,
        }
        target = pf_map.get(self.format.upper(), PixelFormat.RGB)
        return image.convert(target)

    def process(self, data: ImageData, context: FilterContext | None = None) -> ImageData:
        """Convert to specified pixel format."""
        pf = self.format.upper()
        array = data.to_array(pixel_format=pf)
        return ImageData.from_array(array, pixel_format=pf)
