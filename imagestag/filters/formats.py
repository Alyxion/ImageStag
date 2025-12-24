# ImageStag Filters - Format Specifications
"""
Format specification and universal image data container.

This module provides:
- FormatSpec: Describes image data format (pixel format, bit depth, compression)
- ImageData: Universal container for image data in various formats
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from imagestag import Image


class BitDepth(Enum):
    """Bit depth for pixel values."""
    UINT8 = 8      # Standard 8-bit (0-255)
    UINT10 = 10    # 10-bit (0-1023)
    UINT12 = 12    # 12-bit (0-4095)
    UINT16 = 16    # 16-bit (0-65535)
    FLOAT32 = 32   # Float32 (0.0-1.0 typically)

    @property
    def dtype(self) -> np.dtype:
        """Get numpy dtype for this bit depth."""
        if self == BitDepth.FLOAT32:
            return np.dtype(np.float32)
        elif self == BitDepth.UINT16:
            return np.dtype(np.uint16)
        else:
            return np.dtype(np.uint8)

    @property
    def max_value(self) -> int | float:
        """Maximum value for this bit depth."""
        if self == BitDepth.FLOAT32:
            return 1.0
        return (1 << self.value) - 1


class Compression(Enum):
    """Image compression format."""
    NONE = auto()      # Uncompressed pixel data
    JPEG = auto()      # JPEG compressed
    PNG = auto()       # PNG compressed
    WEBP = auto()      # WebP compressed
    BMP = auto()       # BMP format
    GIF = auto()       # GIF format

    @property
    def mime_type(self) -> str:
        """Get MIME type for this compression."""
        return {
            Compression.NONE: 'application/octet-stream',
            Compression.JPEG: 'image/jpeg',
            Compression.PNG: 'image/png',
            Compression.WEBP: 'image/webp',
            Compression.BMP: 'image/bmp',
            Compression.GIF: 'image/gif',
        }[self]

    @classmethod
    def from_mime_type(cls, mime_type: str) -> 'Compression':
        """Get compression from MIME type."""
        mime_map = {
            'image/jpeg': cls.JPEG,
            'image/jpg': cls.JPEG,
            'image/png': cls.PNG,
            'image/webp': cls.WEBP,
            'image/bmp': cls.BMP,
            'image/gif': cls.GIF,
        }
        return mime_map.get(mime_type.lower(), cls.NONE)

    @classmethod
    def from_extension(cls, ext: str) -> 'Compression':
        """Get compression from file extension."""
        ext = ext.lower().lstrip('.')
        ext_map = {
            'jpg': cls.JPEG,
            'jpeg': cls.JPEG,
            'png': cls.PNG,
            'webp': cls.WEBP,
            'bmp': cls.BMP,
            'gif': cls.GIF,
        }
        return ext_map.get(ext, cls.NONE)


@dataclass(frozen=True)
class FormatSpec:
    """Specification for image data format.

    Describes what format image data is in or what formats a filter accepts.

    Examples:
        # Standard 8-bit RGB
        FormatSpec(pixel_format='RGB')

        # OpenCV BGR format
        FormatSpec(pixel_format='BGR')

        # High-precision float
        FormatSpec(pixel_format='RGB', bit_depth=BitDepth.FLOAT32)

        # Compressed JPEG
        FormatSpec(compression=Compression.JPEG)

        # Any format (filter accepts anything)
        FormatSpec.ANY
    """

    pixel_format: str | None = None  # 'RGB', 'BGR', 'RGBA', 'BGRA', 'GRAY', 'HSV', etc.
    bit_depth: BitDepth = BitDepth.UINT8
    compression: Compression = Compression.NONE

    # Special flag for "accepts any format"
    _any: bool = field(default=False, compare=False)

    def matches(self, other: 'FormatSpec') -> bool:
        """Check if this format matches another (for compatibility)."""
        if self._any or other._any:
            return True

        # If either is compressed, compression must match
        if self.compression != Compression.NONE or other.compression != Compression.NONE:
            return self.compression == other.compression

        # For uncompressed, check pixel format and bit depth
        if self.pixel_format is not None and other.pixel_format is not None:
            if self.pixel_format != other.pixel_format:
                return False

        return self.bit_depth == other.bit_depth

    def is_compressed(self) -> bool:
        """Check if this is a compressed format."""
        return self.compression != Compression.NONE

    def __str__(self) -> str:
        if self._any:
            return 'ANY'
        if self.is_compressed():
            return self.compression.name
        parts = []
        if self.pixel_format:
            parts.append(self.pixel_format)
        if self.bit_depth != BitDepth.UINT8:
            parts.append(self.bit_depth.name)
        return '_'.join(parts) if parts else 'UNKNOWN'


# Pre-defined format specs as class attributes
FormatSpec.ANY = FormatSpec(_any=True)
FormatSpec.RGB = FormatSpec(pixel_format='RGB')
FormatSpec.RGBA = FormatSpec(pixel_format='RGBA')
FormatSpec.BGR = FormatSpec(pixel_format='BGR')
FormatSpec.BGRA = FormatSpec(pixel_format='BGRA')
FormatSpec.GRAY = FormatSpec(pixel_format='GRAY')
FormatSpec.HSV = FormatSpec(pixel_format='HSV')
FormatSpec.JPEG = FormatSpec(compression=Compression.JPEG)
FormatSpec.PNG = FormatSpec(compression=Compression.PNG)


@dataclass
class ImageData:
    """Universal container for image data in various formats.

    Can hold:
    - ImageStag Image objects
    - Raw compressed bytes (JPEG, PNG, etc.)
    - Numpy arrays with format information
    - Any combination with metadata

    Examples:
        # From ImageStag Image
        data = ImageData.from_image(img)

        # From JPEG bytes
        data = ImageData.from_bytes(jpeg_bytes, 'image/jpeg')

        # From OpenCV numpy array
        data = ImageData.from_array(cv2_frame, pixel_format='BGR')

        # Convert to desired format
        image = data.to_image()
        rgb_array = data.to_array('RGB')
        jpeg_bytes = data.to_bytes('image/jpeg')
    """

    # Format specification
    format: FormatSpec = field(default_factory=FormatSpec)

    # The actual data (one of these will be populated)
    _image: Any = field(default=None, repr=False)  # ImageStag Image
    _bytes: bytes | None = field(default=None, repr=False)  # Compressed bytes
    _array: np.ndarray | None = field(default=None, repr=False)  # Numpy array

    # Dimensions (for validation/info)
    width: int | None = None
    height: int | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_image(cls, image: 'Image') -> 'ImageData':
        """Create ImageData from an ImageStag Image."""
        from imagestag.pixel_format import PixelFormat

        # Map ImageStag PixelFormat to string
        pf_map = {
            PixelFormat.RGB: 'RGB',
            PixelFormat.RGBA: 'RGBA',
            PixelFormat.BGR: 'BGR',
            PixelFormat.BGRA: 'BGRA',
            PixelFormat.GRAY: 'GRAY',
            PixelFormat.HSV: 'HSV',
        }
        pf_str = pf_map.get(image.pixel_format, 'RGB')

        return cls(
            format=FormatSpec(pixel_format=pf_str),
            _image=image,
            width=image.width,
            height=image.height,
            metadata=image.metadata.copy() if image.metadata else {},
        )

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        mime_type: str | None = None,
        compression: Compression | None = None,
    ) -> 'ImageData':
        """Create ImageData from compressed bytes."""
        if compression is None and mime_type:
            compression = Compression.from_mime_type(mime_type)
        elif compression is None:
            # Try to detect from magic bytes
            compression = cls._detect_compression(data)

        return cls(
            format=FormatSpec(compression=compression or Compression.NONE),
            _bytes=data,
        )

    @classmethod
    def from_array(
        cls,
        array: np.ndarray,
        pixel_format: str = 'RGB',
        bit_depth: BitDepth | None = None,
    ) -> 'ImageData':
        """Create ImageData from a numpy array.

        :param array: Numpy array (H, W) for grayscale or (H, W, C) for color
        :param pixel_format: Pixel format string ('RGB', 'BGR', 'RGBA', 'GRAY', etc.)
        :param bit_depth: Bit depth (auto-detected from dtype if not specified)
        """
        # Auto-detect bit depth from dtype
        if bit_depth is None:
            if array.dtype == np.float32 or array.dtype == np.float64:
                bit_depth = BitDepth.FLOAT32
            elif array.dtype == np.uint16:
                bit_depth = BitDepth.UINT16
            else:
                bit_depth = BitDepth.UINT8

        # Get dimensions
        if len(array.shape) == 2:
            height, width = array.shape
        else:
            height, width = array.shape[:2]

        return cls(
            format=FormatSpec(pixel_format=pixel_format, bit_depth=bit_depth),
            _array=array,
            width=width,
            height=height,
        )

    @staticmethod
    def _detect_compression(data: bytes) -> Compression:
        """Detect compression format from magic bytes."""
        if len(data) < 4:
            return Compression.NONE

        # JPEG: FF D8 FF
        if data[:3] == b'\xff\xd8\xff':
            return Compression.JPEG

        # PNG: 89 50 4E 47
        if data[:4] == b'\x89PNG':
            return Compression.PNG

        # GIF: GIF87a or GIF89a
        if data[:3] == b'GIF':
            return Compression.GIF

        # BMP: BM
        if data[:2] == b'BM':
            return Compression.BMP

        # WebP: RIFF....WEBP
        if data[:4] == b'RIFF' and len(data) >= 12 and data[8:12] == b'WEBP':
            return Compression.WEBP

        return Compression.NONE

    def to_image(self) -> 'Image':
        """Convert to ImageStag Image.

        Decompresses if necessary, converts pixel format if needed.
        """
        from imagestag import Image

        if self._image is not None:
            return self._image

        if self._bytes is not None:
            # Decompress and create Image
            return Image(self._bytes)

        if self._array is not None:
            from imagestag.pixel_format import PixelFormat

            # Map string to PixelFormat enum
            pf_map = {
                'RGB': PixelFormat.RGB,
                'RGBA': PixelFormat.RGBA,
                'BGR': PixelFormat.BGR,
                'BGRA': PixelFormat.BGRA,
                'GRAY': PixelFormat.GRAY,
                'HSV': PixelFormat.HSV,
            }
            pf = pf_map.get(self.format.pixel_format, PixelFormat.RGB)

            # Convert bit depth if needed
            array = self._array
            if self.format.bit_depth == BitDepth.FLOAT32:
                array = (np.clip(array, 0, 1) * 255).astype(np.uint8)
            elif self.format.bit_depth != BitDepth.UINT8:
                # Scale to 8-bit
                max_val = self.format.bit_depth.max_value
                array = (array.astype(np.float32) / max_val * 255).astype(np.uint8)

            return Image(array, pixel_format=pf)

        raise ValueError("ImageData has no data")

    def to_bytes(
        self,
        compression: Compression | str = Compression.JPEG,
        quality: int = 90,
    ) -> bytes:
        """Convert to compressed bytes.

        :param compression: Target compression format
        :param quality: Compression quality (for JPEG)
        """
        if isinstance(compression, str):
            compression = Compression.from_mime_type(compression)

        # If already in this compression format, return directly
        if self._bytes is not None and self.format.compression == compression:
            return self._bytes

        # Convert to Image first, then encode
        image = self.to_image()

        format_map = {
            Compression.JPEG: 'jpeg',
            Compression.PNG: 'png',
            Compression.BMP: 'bmp',
            Compression.GIF: 'gif',
        }
        fmt = format_map.get(compression, 'png')
        return image.encode(fmt, quality=quality)

    def to_array(
        self,
        pixel_format: str = 'RGB',
        bit_depth: BitDepth = BitDepth.UINT8,
    ) -> np.ndarray:
        """Convert to numpy array with specified format.

        :param pixel_format: Target pixel format ('RGB', 'BGR', 'GRAY', etc.)
        :param bit_depth: Target bit depth
        """
        from imagestag.pixel_format import PixelFormat

        # If already the right format, return directly
        if (self._array is not None and
            self.format.pixel_format == pixel_format and
            self.format.bit_depth == bit_depth):
            return self._array

        # Convert via Image
        image = self.to_image()

        pf_map = {
            'RGB': PixelFormat.RGB,
            'RGBA': PixelFormat.RGBA,
            'BGR': PixelFormat.BGR,
            'BGRA': PixelFormat.BGRA,
            'GRAY': PixelFormat.GRAY,
        }
        pf = pf_map.get(pixel_format, PixelFormat.RGB)
        array = image.get_pixels(pf)

        # Convert bit depth if needed
        if bit_depth == BitDepth.FLOAT32:
            array = array.astype(np.float32) / 255.0
        elif bit_depth != BitDepth.UINT8:
            max_val = bit_depth.max_value
            array = (array.astype(np.float32) / 255.0 * max_val).astype(np.uint16)

        return array

    def to_pil(self) -> 'Any':
        """Convert to PIL Image.

        :returns: PIL.Image.Image object
        """
        from PIL import Image as PILImage

        if self._image is not None:
            return self._image.to_pil()

        # Convert via array
        array = self.to_array('RGB')
        return PILImage.fromarray(array)

    def to_cv(self) -> np.ndarray:
        """Convert to OpenCV-compatible numpy array (BGR format).

        This is a convenience method for OpenCV integration.
        Returns a numpy array in BGR format, which is the standard for OpenCV.

        :returns: Numpy array in BGR format (H, W, 3) with dtype uint8
        """
        return self.to_array('BGR')

    def get_format(self) -> FormatSpec:
        """Get the current format specification."""
        return self.format

    def convert_to(self, target_format: FormatSpec) -> 'ImageData':
        """Convert to a different format, returning new ImageData."""
        if self.format.matches(target_format):
            return self  # Already compatible

        if target_format.is_compressed():
            # Convert to compressed bytes
            data = self.to_bytes(target_format.compression)
            return ImageData.from_bytes(data, compression=target_format.compression)
        else:
            # Convert to array with specified format
            array = self.to_array(
                pixel_format=target_format.pixel_format or 'RGB',
                bit_depth=target_format.bit_depth,
            )
            return ImageData.from_array(
                array,
                pixel_format=target_format.pixel_format or 'RGB',
                bit_depth=target_format.bit_depth,
            )

    @property
    def has_data(self) -> bool:
        """Check if this container has any data."""
        return self._image is not None or self._bytes is not None or self._array is not None
