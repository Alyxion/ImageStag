"""Color adjustment filters."""

import numpy as np
import imagestag_rust

from .base import BaseFilter
from .registry import register_filter


@register_filter("grayscale")
class GrayscaleFilter(BaseFilter):
    """Convert to grayscale."""

    name = "Grayscale"
    description = "Convert image to grayscale"
    category = "color"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return []

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.grayscale_rgba(image)


@register_filter("invert")
class InvertFilter(BaseFilter):
    """Invert colors."""

    name = "Invert Colors"
    description = "Invert all colors in the image"
    category = "color"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return []

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.invert(image)


@register_filter("brightness_contrast")
class BrightnessContrastFilter(BaseFilter):
    """Adjust brightness, contrast, and gamma."""

    name = "Brightness/Contrast"
    description = "Adjust image brightness, contrast, and gamma"
    category = "color"
    version = 2

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "brightness",
                "name": "Brightness",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
                "suffix": "%",
            },
            {
                "id": "contrast",
                "name": "Contrast",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
                "suffix": "%",
            },
            {
                "id": "gamma",
                "name": "Gamma",
                "type": "range",
                "min": 0.1,
                "max": 3.0,
                "step": 0.01,
                "default": 1.0,
            },
        ]

    def apply(self, image: np.ndarray, brightness: int = 0, contrast: int = 0, gamma: float = 1.0) -> np.ndarray:
        result = imagestag_rust.brightness(image, brightness / 100.0)
        result = imagestag_rust.contrast(result, contrast / 100.0)
        if gamma != 1.0:
            result = imagestag_rust.gamma(result, float(gamma))
        return result


@register_filter("sepia")
class SepiaFilter(BaseFilter):
    """Apply sepia tone."""

    name = "Sepia"
    description = "Apply vintage sepia tone effect"
    category = "color"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "intensity",
                "name": "Intensity",
                "type": "range",
                "min": 0,
                "max": 100,
                "step": 1,
                "default": 100,
                "suffix": "%",
            }
        ]

    def apply(self, image: np.ndarray, intensity: int = 100) -> np.ndarray:
        return imagestag_rust.sepia(image, intensity / 100.0)


@register_filter("hue_saturation")
class HueSaturationFilter(BaseFilter):
    """Adjust hue, saturation, lightness, vibrance, and temperature."""

    name = "HSL / Color"
    description = "Adjust hue, saturation, lightness, vibrance, and temperature"
    category = "color"
    version = 2

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "hue",
                "name": "Hue",
                "type": "range",
                "min": -180,
                "max": 180,
                "step": 1,
                "default": 0,
                "suffix": "°",
            },
            {
                "id": "saturation",
                "name": "Saturation",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
                "suffix": "%",
            },
            {
                "id": "lightness",
                "name": "Lightness",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
                "suffix": "%",
            },
            {
                "id": "vibrance",
                "name": "Vibrance",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
                "suffix": "%",
            },
            {
                "id": "temperature",
                "name": "Temperature",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
            },
        ]

    def apply(self, image: np.ndarray, hue: int = 0, saturation: int = 0,
              lightness: int = 0, vibrance: int = 0, temperature: int = 0) -> np.ndarray:
        result = image
        if hue != 0:
            result = imagestag_rust.hue_shift(result, float(hue))
        if saturation != 0:
            result = imagestag_rust.saturation(result, saturation / 100.0)
        if lightness != 0:
            result = imagestag_rust.brightness(result, lightness / 100.0)
        if vibrance != 0:
            result = imagestag_rust.vibrance(result, vibrance / 100.0)
        if temperature != 0:
            result = imagestag_rust.temperature(result, temperature / 100.0)
        return result


@register_filter("color_balance")
class ColorBalanceFilter(BaseFilter):
    """Adjust color balance (shadows, midtones, highlights)."""

    name = "Color Balance"
    description = "Adjust color balance for shadows, midtones, and highlights"
    category = "color"
    version = 2

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "range",
                "name": "Tonal Range",
                "type": "select",
                "options": ["shadows", "midtones", "highlights"],
                "default": "midtones",
            },
            {
                "id": "red",
                "name": "Cyan/Red",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
            },
            {
                "id": "green",
                "name": "Magenta/Green",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
            },
            {
                "id": "blue",
                "name": "Yellow/Blue",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
            },
        ]

    def apply(self, image: np.ndarray, red: int = 0, green: int = 0, blue: int = 0,
              range: str = "midtones", **kwargs) -> np.ndarray:
        r, g, b = red / 100.0, green / 100.0, blue / 100.0
        vals = [r, g, b]
        shadows = vals if range == "shadows" else [0.0, 0.0, 0.0]
        midtones = vals if range == "midtones" else [0.0, 0.0, 0.0]
        highlights = vals if range == "highlights" else [0.0, 0.0, 0.0]
        return imagestag_rust.color_balance(image, shadows, midtones, highlights)


@register_filter("auto_contrast")
class AutoContrastFilter(BaseFilter):
    """Automatic contrast stretch."""

    name = "Auto Contrast"
    description = "Automatically stretch contrast for optimal range"
    category = "color"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "clip_percent",
                "name": "Clip Percent",
                "type": "range",
                "min": 0.0,
                "max": 5.0,
                "step": 0.1,
                "default": 1.0,
                "suffix": "%",
            },
        ]

    def apply(self, image: np.ndarray, clip_percent: float = 1.0) -> np.ndarray:
        return imagestag_rust.auto_levels(image, clip_percent / 100.0)


@register_filter("equalize_histogram")
class EqualizeHistogramFilter(BaseFilter):
    """Histogram equalization."""

    name = "Equalize Histogram"
    description = "Enhance contrast using histogram equalization"
    category = "color"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return []

    def apply(self, image: np.ndarray, **kwargs) -> np.ndarray:
        return imagestag_rust.equalize_histogram(image)


@register_filter("channel_mixer")
class ChannelMixerFilter(BaseFilter):
    """Mix color channels."""

    name = "Channel Mixer"
    description = "Mix and swap color channels"
    category = "color"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "red_channel",
                "name": "Red Source",
                "type": "select",
                "options": ["red", "green", "blue"],
                "default": "red",
            },
            {
                "id": "green_channel",
                "name": "Green Source",
                "type": "select",
                "options": ["red", "green", "blue"],
                "default": "green",
            },
            {
                "id": "blue_channel",
                "name": "Blue Source",
                "type": "select",
                "options": ["red", "green", "blue"],
                "default": "blue",
            },
        ]

    def apply(self, image: np.ndarray, red_channel: str = "red", green_channel: str = "green", blue_channel: str = "blue") -> np.ndarray:
        channel_map = {"red": 0, "green": 1, "blue": 2}
        return imagestag_rust.channel_mixer(
            image,
            channel_map[red_channel],
            channel_map[green_channel],
            channel_map[blue_channel],
        )


@register_filter("exposure")
class ExposureFilter(BaseFilter):
    """Adjust exposure, offset, and gamma."""

    name = "Exposure"
    description = "Adjust image exposure, offset, and gamma"
    category = "color"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "exposure_val",
                "name": "Exposure",
                "type": "range",
                "min": -3.0,
                "max": 3.0,
                "step": 0.01,
                "default": 0.0,
                "suffix": "EV",
            },
            {
                "id": "offset",
                "name": "Offset",
                "type": "range",
                "min": -0.5,
                "max": 0.5,
                "step": 0.01,
                "default": 0.0,
            },
            {
                "id": "gamma_val",
                "name": "Gamma",
                "type": "range",
                "min": 0.1,
                "max": 5.0,
                "step": 0.01,
                "default": 1.0,
            },
        ]

    def apply(self, image: np.ndarray, exposure_val: float = 0.0, offset: float = 0.0, gamma_val: float = 1.0) -> np.ndarray:
        return imagestag_rust.exposure(image, float(exposure_val), float(offset), float(gamma_val))


@register_filter("levels")
class LevelsFilter(BaseFilter):
    """Input/output levels with gamma."""

    name = "Levels"
    description = "Adjust input/output levels with gamma correction"
    category = "color"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "in_black",
                "name": "Input Black",
                "type": "range",
                "min": 0,
                "max": 255,
                "step": 1,
                "default": 0,
            },
            {
                "id": "in_white",
                "name": "Input White",
                "type": "range",
                "min": 0,
                "max": 255,
                "step": 1,
                "default": 255,
            },
            {
                "id": "gamma",
                "name": "Gamma",
                "type": "range",
                "min": 0.1,
                "max": 5.0,
                "step": 0.01,
                "default": 1.0,
            },
            {
                "id": "out_black",
                "name": "Output Black",
                "type": "range",
                "min": 0,
                "max": 255,
                "step": 1,
                "default": 0,
            },
            {
                "id": "out_white",
                "name": "Output White",
                "type": "range",
                "min": 0,
                "max": 255,
                "step": 1,
                "default": 255,
            },
        ]

    def apply(self, image: np.ndarray, in_black: int = 0, in_white: int = 255,
              gamma: float = 1.0, out_black: int = 0, out_white: int = 255) -> np.ndarray:
        return imagestag_rust.levels(image, int(in_black), int(in_white), int(out_black), int(out_white), float(gamma))


