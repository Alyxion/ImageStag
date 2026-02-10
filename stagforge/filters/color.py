"""Color adjustment filters."""

from typing import ClassVar

import numpy as np
import imagestag_rust
from pydantic import Field

from .base import BaseFilter
from .registry import register_filter


@register_filter("grayscale")
class GrayscaleFilter(BaseFilter):
    """Convert to grayscale."""

    filter_type: ClassVar[str] = "grayscale"
    name: ClassVar[str] = "Grayscale"
    description: ClassVar[str] = "Convert image to grayscale"
    category: ClassVar[str] = "color"
    VERSION: ClassVar[int] = 1

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.grayscale_rgba(image)


@register_filter("invert")
class InvertFilter(BaseFilter):
    """Invert colors."""

    filter_type: ClassVar[str] = "invert"
    name: ClassVar[str] = "Invert Colors"
    description: ClassVar[str] = "Invert all colors in the image"
    category: ClassVar[str] = "color"
    VERSION: ClassVar[int] = 1

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.invert(image)


@register_filter("brightness_contrast")
class BrightnessContrastFilter(BaseFilter):
    """Adjust brightness, contrast, and gamma."""

    filter_type: ClassVar[str] = "brightness_contrast"
    name: ClassVar[str] = "Brightness/Contrast"
    description: ClassVar[str] = "Adjust image brightness, contrast, and gamma"
    category: ClassVar[str] = "color"
    VERSION: ClassVar[int] = 2

    brightness: int = Field(default=0, ge=-100, le=100,
                            json_schema_extra={"step": 1, "suffix": "%",
                                               "display_name": "Brightness"})
    contrast: int = Field(default=0, ge=-100, le=100,
                          json_schema_extra={"step": 1, "suffix": "%",
                                             "display_name": "Contrast"})
    gamma: float = Field(default=1.0, ge=0.1, le=3.0,
                         json_schema_extra={"step": 0.01,
                                            "display_name": "Gamma"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        result = imagestag_rust.brightness(image, self.brightness / 100.0)
        result = imagestag_rust.contrast(result, self.contrast / 100.0)
        if self.gamma != 1.0:
            result = imagestag_rust.gamma(result, float(self.gamma))
        return result


@register_filter("sepia")
class SepiaFilter(BaseFilter):
    """Apply sepia tone."""

    filter_type: ClassVar[str] = "sepia"
    name: ClassVar[str] = "Sepia"
    description: ClassVar[str] = "Apply vintage sepia tone effect"
    category: ClassVar[str] = "color"
    VERSION: ClassVar[int] = 1

    intensity: int = Field(default=100, ge=0, le=100,
                           json_schema_extra={"step": 1, "suffix": "%",
                                              "display_name": "Intensity"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.sepia(image, self.intensity / 100.0)


@register_filter("hue_saturation")
class HueSaturationFilter(BaseFilter):
    """Adjust hue, saturation, lightness, vibrance, and temperature."""

    filter_type: ClassVar[str] = "hue_saturation"
    name: ClassVar[str] = "HSL / Color"
    description: ClassVar[str] = "Adjust hue, saturation, lightness, vibrance, and temperature"
    category: ClassVar[str] = "color"
    VERSION: ClassVar[int] = 2

    hue: int = Field(default=0, ge=-180, le=180,
                     json_schema_extra={"step": 1, "suffix": "\u00b0",
                                        "display_name": "Hue"})
    saturation: int = Field(default=0, ge=-100, le=100,
                            json_schema_extra={"step": 1, "suffix": "%",
                                               "display_name": "Saturation"})
    lightness: int = Field(default=0, ge=-100, le=100,
                           json_schema_extra={"step": 1, "suffix": "%",
                                              "display_name": "Lightness"})
    vibrance: int = Field(default=0, ge=-100, le=100,
                          json_schema_extra={"step": 1, "suffix": "%",
                                             "display_name": "Vibrance"})
    temperature: int = Field(default=0, ge=-100, le=100,
                             json_schema_extra={"step": 1,
                                                "display_name": "Temperature"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        result = image
        if self.hue != 0:
            result = imagestag_rust.hue_shift(result, float(self.hue))
        if self.saturation != 0:
            result = imagestag_rust.saturation(result, self.saturation / 100.0)
        if self.lightness != 0:
            result = imagestag_rust.brightness(result, self.lightness / 100.0)
        if self.vibrance != 0:
            result = imagestag_rust.vibrance(result, self.vibrance / 100.0)
        if self.temperature != 0:
            result = imagestag_rust.temperature(result, self.temperature / 100.0)
        return result


@register_filter("color_balance")
class ColorBalanceFilter(BaseFilter):
    """Adjust color balance (shadows, midtones, highlights)."""

    filter_type: ClassVar[str] = "color_balance"
    name: ClassVar[str] = "Color Balance"
    description: ClassVar[str] = "Adjust color balance for shadows, midtones, and highlights"
    category: ClassVar[str] = "color"
    VERSION: ClassVar[int] = 2

    tonal_range: str = Field(default="midtones",
                             json_schema_extra={"options": ["shadows", "midtones", "highlights"],
                                                "display_name": "Tonal Range"})
    red: int = Field(default=0, ge=-100, le=100,
                     json_schema_extra={"step": 1, "display_name": "Cyan/Red"})
    green: int = Field(default=0, ge=-100, le=100,
                       json_schema_extra={"step": 1, "display_name": "Magenta/Green"})
    blue: int = Field(default=0, ge=-100, le=100,
                      json_schema_extra={"step": 1, "display_name": "Yellow/Blue"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        r, g, b = self.red / 100.0, self.green / 100.0, self.blue / 100.0
        vals = [r, g, b]
        shadows = vals if self.tonal_range == "shadows" else [0.0, 0.0, 0.0]
        midtones = vals if self.tonal_range == "midtones" else [0.0, 0.0, 0.0]
        highlights = vals if self.tonal_range == "highlights" else [0.0, 0.0, 0.0]
        return imagestag_rust.color_balance(image, shadows, midtones, highlights)


@register_filter("auto_contrast")
class AutoContrastFilter(BaseFilter):
    """Automatic contrast stretch."""

    filter_type: ClassVar[str] = "auto_contrast"
    name: ClassVar[str] = "Auto Contrast"
    description: ClassVar[str] = "Automatically stretch contrast for optimal range"
    category: ClassVar[str] = "color"
    VERSION: ClassVar[int] = 1

    clip_percent: float = Field(default=1.0, ge=0.0, le=5.0,
                                json_schema_extra={"step": 0.1, "suffix": "%",
                                                   "display_name": "Clip Percent"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.auto_levels(image, self.clip_percent / 100.0)


@register_filter("equalize_histogram")
class EqualizeHistogramFilter(BaseFilter):
    """Histogram equalization."""

    filter_type: ClassVar[str] = "equalize_histogram"
    name: ClassVar[str] = "Equalize Histogram"
    description: ClassVar[str] = "Enhance contrast using histogram equalization"
    category: ClassVar[str] = "color"
    VERSION: ClassVar[int] = 1

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.equalize_histogram(image)


@register_filter("channel_mixer")
class ChannelMixerFilter(BaseFilter):
    """Mix color channels."""

    filter_type: ClassVar[str] = "channel_mixer"
    name: ClassVar[str] = "Channel Mixer"
    description: ClassVar[str] = "Mix and swap color channels"
    category: ClassVar[str] = "color"
    VERSION: ClassVar[int] = 1

    red_channel: str = Field(default="red",
                             json_schema_extra={"options": ["red", "green", "blue"],
                                                "display_name": "Red Source"})
    green_channel: str = Field(default="green",
                               json_schema_extra={"options": ["red", "green", "blue"],
                                                  "display_name": "Green Source"})
    blue_channel: str = Field(default="blue",
                              json_schema_extra={"options": ["red", "green", "blue"],
                                                 "display_name": "Blue Source"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        channel_map = {"red": 0, "green": 1, "blue": 2}
        return imagestag_rust.channel_mixer(
            image,
            channel_map[self.red_channel],
            channel_map[self.green_channel],
            channel_map[self.blue_channel],
        )


@register_filter("exposure")
class ExposureFilter(BaseFilter):
    """Adjust exposure, offset, and gamma."""

    filter_type: ClassVar[str] = "exposure"
    name: ClassVar[str] = "Exposure"
    description: ClassVar[str] = "Adjust image exposure, offset, and gamma"
    category: ClassVar[str] = "color"
    VERSION: ClassVar[int] = 1

    exposure_val: float = Field(default=0.0, ge=-3.0, le=3.0,
                                json_schema_extra={"step": 0.01, "suffix": "EV",
                                                   "display_name": "Exposure"})
    offset: float = Field(default=0.0, ge=-0.5, le=0.5,
                          json_schema_extra={"step": 0.01,
                                             "display_name": "Offset"})
    gamma_val: float = Field(default=1.0, ge=0.1, le=5.0,
                             json_schema_extra={"step": 0.01,
                                                "display_name": "Gamma"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.exposure(image, float(self.exposure_val),
                                       float(self.offset), float(self.gamma_val))


@register_filter("levels")
class LevelsFilter(BaseFilter):
    """Input/output levels with gamma."""

    filter_type: ClassVar[str] = "levels"
    name: ClassVar[str] = "Levels"
    description: ClassVar[str] = "Adjust input/output levels with gamma correction"
    category: ClassVar[str] = "color"
    VERSION: ClassVar[int] = 1

    in_black: int = Field(default=0, ge=0, le=255,
                          json_schema_extra={"step": 1, "display_name": "Input Black"})
    in_white: int = Field(default=255, ge=0, le=255,
                          json_schema_extra={"step": 1, "display_name": "Input White"})
    gamma: float = Field(default=1.0, ge=0.1, le=5.0,
                         json_schema_extra={"step": 0.01, "display_name": "Gamma"})
    out_black: int = Field(default=0, ge=0, le=255,
                           json_schema_extra={"step": 1, "display_name": "Output Black"})
    out_white: int = Field(default=255, ge=0, le=255,
                           json_schema_extra={"step": 1, "display_name": "Output White"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.levels(image, int(self.in_black), int(self.in_white),
                                     int(self.out_black), int(self.out_white),
                                     float(self.gamma))
