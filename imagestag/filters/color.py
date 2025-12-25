# ImageStag Filters - Color Adjustments
"""
Color adjustment filters: Brightness, Contrast, Saturation, Grayscale, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from PIL import ImageEnhance, ImageOps
from PIL import Image as PILImage

from .base import Filter, FilterContext, register_filter
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class Brightness(Filter):
    """Adjust image brightness.

    factor: 0.0 = black, 1.0 = original, 2.0 = 2x bright
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    factor: float = 1.0
    _primary_param = 'factor'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        enhancer = ImageEnhance.Brightness(pil_img)
        result = enhancer.enhance(self.factor)
        return Img(result)


@register_filter
@dataclass
class Contrast(Filter):
    """Adjust image contrast.

    factor: 0.0 = gray, 1.0 = original, 2.0 = high contrast
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    factor: float = 1.0
    _primary_param = 'factor'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        enhancer = ImageEnhance.Contrast(pil_img)
        result = enhancer.enhance(self.factor)
        return Img(result)


@register_filter
@dataclass
class Saturation(Filter):
    """Adjust color saturation.

    factor: 0.0 = grayscale, 1.0 = original, 2.0 = vivid
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    factor: float = 1.0
    _primary_param = 'factor'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        enhancer = ImageEnhance.Color(pil_img)
        result = enhancer.enhance(self.factor)
        return Img(result)


@register_filter
@dataclass
class Sharpness(Filter):
    """Adjust image sharpness.

    factor: 0.0 = blurry, 1.0 = original, 2.0 = sharper
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    factor: float = 1.0
    _primary_param = 'factor'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        enhancer = ImageEnhance.Sharpness(pil_img)
        result = enhancer.enhance(self.factor)
        return Img(result)


@register_filter
@dataclass
class Grayscale(Filter):
    """Convert to grayscale."""

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    method: str = 'luminosity'  # 'luminosity', 'average', 'lightness'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        result = pil_img.convert('L').convert('RGB')
        return Img(result)


@register_filter
@dataclass
class Invert(Filter):
    """Invert colors (negative)."""

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        pil_img = image.to_pil()
        # Handle RGBA by inverting only RGB channels
        if pil_img.mode == 'RGBA':
            r, g, b, a = pil_img.split()
            rgb = PILImage.merge('RGB', (r, g, b))
            inverted = ImageOps.invert(rgb)
            r, g, b = inverted.split()
            result = PILImage.merge('RGBA', (r, g, b, a))
        else:
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            result = ImageOps.invert(pil_img)
        return Img(result)


@register_filter
@dataclass
class Threshold(Filter):
    """Binary threshold filter.

    Pixels above threshold become white, below become black.
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]
    _supports_inplace: ClassVar[bool] = True

    value: int = 128  # 0-255
    _primary_param = 'value'

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        from imagestag import Image as Img
        import numpy as np

        pil_img = image.to_pil()
        # Convert to grayscale first
        gray = pil_img.convert('L')
        # Apply threshold
        pixels = np.array(gray)
        binary = np.where(pixels > self.value, 255, 0).astype(np.uint8)
        # Convert back to RGB
        result = PILImage.fromarray(binary, mode='L').convert('RGB')
        return Img(result)


@register_filter
@dataclass
class AutoContrast(Filter):
    """Automatically adjust contrast based on image histogram.

    Normalizes the image contrast by remapping the darkest pixels to black
    and lightest to white.

    Parameters:
        cutoff: Percentage of lightest/darkest pixels to ignore (default 0)
        preserve_tone: If True, preserve overall tonal balance (default False)

    Example:
        'autocontrast()' or 'autocontrast(cutoff=2)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]
    _primary_param: ClassVar[str] = 'cutoff'

    cutoff: float = 0.0
    preserve_tone: bool = False

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()

        # Handle RGBA by processing only RGB
        if pil_img.mode == 'RGBA':
            r, g, b, a = pil_img.split()
            rgb = PILImage.merge('RGB', (r, g, b))
            result_rgb = ImageOps.autocontrast(rgb, cutoff=self.cutoff, preserve_tone=self.preserve_tone)
            r, g, b = result_rgb.split()
            result = PILImage.merge('RGBA', (r, g, b, a))
        else:
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            result = ImageOps.autocontrast(pil_img, cutoff=self.cutoff, preserve_tone=self.preserve_tone)

        return Img(result)


@register_filter
@dataclass
class Posterize(Filter):
    """Reduce the number of bits per color channel.

    Creates a posterized/banded effect by reducing color depth.

    Parameters:
        bits: Number of bits to keep per channel (1-8, default 4)

    Example:
        'posterize(4)' - keep 4 bits per channel (16 levels)
        'posterize(bits=2)' - keep 2 bits (4 levels, strong effect)
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]
    _primary_param: ClassVar[str] = 'bits'

    bits: int = 4

    def __post_init__(self):
        self.bits = max(1, min(8, self.bits))

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()

        # Handle RGBA by processing only RGB
        if pil_img.mode == 'RGBA':
            r, g, b, a = pil_img.split()
            rgb = PILImage.merge('RGB', (r, g, b))
            result_rgb = ImageOps.posterize(rgb, self.bits)
            r, g, b = result_rgb.split()
            result = PILImage.merge('RGBA', (r, g, b, a))
        else:
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            result = ImageOps.posterize(pil_img, self.bits)

        return Img(result)


@register_filter
@dataclass
class Solarize(Filter):
    """Invert pixels above a threshold for a solarized effect.

    Creates a partially inverted image, simulating the Sabattier effect
    from darkroom photography.

    Parameters:
        threshold: Pixel value threshold (0-255, default 128)

    Example:
        'solarize()' or 'solarize(threshold=100)'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]
    _primary_param: ClassVar[str] = 'threshold'

    threshold: int = 128

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()

        # Handle RGBA by processing only RGB
        if pil_img.mode == 'RGBA':
            r, g, b, a = pil_img.split()
            rgb = PILImage.merge('RGB', (r, g, b))
            result_rgb = ImageOps.solarize(rgb, self.threshold)
            r, g, b = result_rgb.split()
            result = PILImage.merge('RGBA', (r, g, b, a))
        else:
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            result = ImageOps.solarize(pil_img, self.threshold)

        return Img(result)


@register_filter
@dataclass
class Equalize(Filter):
    """Equalize the image histogram.

    Applies a non-linear mapping to the input image to create
    a uniform distribution of grayscale values.

    Example:
        'equalize()'
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.PIL]

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        pil_img = image.to_pil()

        # Handle RGBA by processing only RGB
        if pil_img.mode == 'RGBA':
            r, g, b, a = pil_img.split()
            rgb = PILImage.merge('RGB', (r, g, b))
            result_rgb = ImageOps.equalize(rgb)
            r, g, b = result_rgb.split()
            result = PILImage.merge('RGBA', (r, g, b, a))
        else:
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            result = ImageOps.equalize(pil_img)

        return Img(result)
