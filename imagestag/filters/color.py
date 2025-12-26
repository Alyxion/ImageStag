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


@register_filter
@dataclass
class FalseColor(Filter):
    """Apply false color using matplotlib colormaps.

    Converts image to grayscale and maps values through a colormap.
    RGB input is automatically converted to grayscale first.
    Preserves input framework (PIL in → PIL out, CV in → CV out).

    :param colormap: Matplotlib colormap name (e.g., 'viridis', 'hot', 'jet', 'inferno')
    :param input_min: Minimum input value for normalization (default 0.0)
    :param input_max: Maximum input value for normalization (default 255.0)
    :param reverse: Reverse the colormap direction (default False)

    Example:
        'falsecolor hot'
        'falsecolor viridis reverse=true'
        'falsecolor jet input_min=50 input_max=200'

    Common colormaps:
        Sequential: viridis, plasma, inferno, magma, cividis
        Diverging: coolwarm, RdBu, seismic
        Thermal: hot, afmhot, gist_heat
        Other: jet, rainbow, turbo, gray
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.CV, ImsFramework.PIL, ImsFramework.RAW]
    _preserve_framework: ClassVar[bool] = True  # Preserve input framework
    _primary_param: ClassVar[str] = 'colormap'

    colormap: str = 'viridis'
    input_min: float = 0.0
    input_max: float = 255.0
    reverse: bool = False

    # Class-level LUT cache for fast repeated application (RGB and BGR versions)
    _lut_cache: ClassVar[dict[str, 'np.ndarray']] = {}

    def _get_lut(self, bgr: bool = False) -> 'np.ndarray':
        """Get or create the colormap LUT (256 RGB or BGR values).

        :param bgr: If True, return BGR order for OpenCV. If False, return RGB.
        """
        import numpy as np

        # Cache key includes colormap name, reverse flag, and color order
        cache_key = f"{self.colormap}_{self.reverse}_{'bgr' if bgr else 'rgb'}"
        if cache_key in FalseColor._lut_cache:
            return FalseColor._lut_cache[cache_key]

        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError(
                "matplotlib is required for FalseColor filter. "
                "Install with: poetry add matplotlib"
            )

        # Get colormap
        cmap_name = f"{self.colormap}_r" if self.reverse else self.colormap
        try:
            cmap = plt.get_cmap(cmap_name)
        except ValueError:
            raise ValueError(
                f"Unknown colormap: '{self.colormap}'. "
                f"See matplotlib colormaps: https://matplotlib.org/stable/users/explain/colors/colormaps.html"
            )

        # Create LUT: 256 entries mapping grayscale to RGB
        indices = np.linspace(0, 1, 256)
        lut = (cmap(indices)[:, :3] * 255).astype(np.uint8)

        # Convert to BGR if requested
        if bgr:
            lut = lut[:, ::-1]

        # Cache the LUT
        FalseColor._lut_cache[cache_key] = lut
        return lut

    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        from imagestag.definitions import ImsFramework
        import numpy as np

        # Detect input framework to preserve it
        input_framework = image.framework
        use_bgr = input_framework == ImsFramework.CV

        # Get grayscale pixels (auto-converts RGB/BGR to grayscale)
        gray = image.get_pixels(PixelFormat.GRAY)

        # Get precomputed LUT (RGB or BGR depending on input framework)
        lut = self._get_lut(bgr=use_bgr)

        # Handle custom input range by rescaling to 0-255
        if self.input_min != 0.0 or self.input_max != 255.0:
            input_range = self.input_max - self.input_min
            if input_range <= 0:
                input_range = 255.0
            # Rescale to 0-255 range for LUT indexing
            gray = ((gray.astype(np.float32) - self.input_min) / input_range * 255)
            gray = np.clip(gray, 0, 255).astype(np.uint8)

        # Apply LUT using numpy advanced indexing (very fast)
        result = lut[gray]

        # Return in same framework as input
        if use_bgr:
            return Img(result, pixel_format=PixelFormat.BGR, framework=ImsFramework.CV)
        else:
            return Img(result, pixel_format=PixelFormat.RGB)
