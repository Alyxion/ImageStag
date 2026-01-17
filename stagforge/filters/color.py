"""Color adjustment filters."""

import numpy as np
from skimage import color as skcolor

from .base import BaseFilter
from .registry import register_filter


@register_filter("grayscale")
class GrayscaleFilter(BaseFilter):
    """Convert to grayscale."""

    name = "Grayscale"
    description = "Convert image to grayscale"
    category = "color"

    @classmethod
    def get_params_schema(cls):
        return []

    def apply(self, image: np.ndarray) -> np.ndarray:
        rgb = image[:, :, :3]
        gray = skcolor.rgb2gray(rgb)
        gray = (gray * 255).astype(np.uint8)

        result = np.stack([gray, gray, gray, image[:, :, 3]], axis=2)
        return result


@register_filter("invert")
class InvertFilter(BaseFilter):
    """Invert colors."""

    name = "Invert Colors"
    description = "Invert all colors in the image"
    category = "color"

    @classmethod
    def get_params_schema(cls):
        return []

    def apply(self, image: np.ndarray) -> np.ndarray:
        result = image.copy()
        result[:, :, :3] = 255 - image[:, :, :3]
        return result


@register_filter("brightness_contrast")
class BrightnessContrastFilter(BaseFilter):
    """Adjust brightness and contrast."""

    name = "Brightness/Contrast"
    description = "Adjust image brightness and contrast"
    category = "color"

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
            },
            {
                "id": "contrast",
                "name": "Contrast",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
            },
        ]

    def apply(self, image: np.ndarray, brightness: int = 0, contrast: int = 0) -> np.ndarray:
        result = image.copy().astype(np.float32)

        # Apply brightness
        result[:, :, :3] += brightness * 2.55  # Scale to 0-255 range

        # Apply contrast
        factor = (259 * (contrast + 255)) / (255 * (259 - contrast))
        result[:, :, :3] = factor * (result[:, :, :3] - 128) + 128

        # Clamp and convert back
        result = np.clip(result, 0, 255).astype(np.uint8)
        return result


@register_filter("sepia")
class SepiaFilter(BaseFilter):
    """Apply sepia tone."""

    name = "Sepia"
    description = "Apply vintage sepia tone effect"
    category = "color"

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
            }
        ]

    def apply(self, image: np.ndarray, intensity: int = 100) -> np.ndarray:
        result = image.copy().astype(np.float32)
        factor = intensity / 100.0

        r = result[:, :, 0]
        g = result[:, :, 1]
        b = result[:, :, 2]

        # Sepia transformation matrix
        new_r = r * (1 - factor) + (r * 0.393 + g * 0.769 + b * 0.189) * factor
        new_g = g * (1 - factor) + (r * 0.349 + g * 0.686 + b * 0.168) * factor
        new_b = b * (1 - factor) + (r * 0.272 + g * 0.534 + b * 0.131) * factor

        result[:, :, 0] = np.clip(new_r, 0, 255)
        result[:, :, 1] = np.clip(new_g, 0, 255)
        result[:, :, 2] = np.clip(new_b, 0, 255)

        return result.astype(np.uint8)


@register_filter("hue_saturation")
class HueSaturationFilter(BaseFilter):
    """Adjust hue, saturation, and lightness."""

    name = "Hue/Saturation"
    description = "Adjust hue, saturation, and lightness values"
    category = "color"

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
            },
            {
                "id": "saturation",
                "name": "Saturation",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
            },
            {
                "id": "lightness",
                "name": "Lightness",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 0,
            },
        ]

    def apply(self, image: np.ndarray, hue: int = 0, saturation: int = 0, lightness: int = 0) -> np.ndarray:
        import cv2

        rgb = image[:, :, :3]
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)

        # Adjust hue (wraps around)
        hsv[:, :, 0] = (hsv[:, :, 0] + hue / 2) % 180

        # Adjust saturation
        if saturation >= 0:
            hsv[:, :, 1] = hsv[:, :, 1] * (1 + saturation / 100)
        else:
            hsv[:, :, 1] = hsv[:, :, 1] * (1 + saturation / 100)

        # Adjust lightness (value)
        hsv[:, :, 2] = hsv[:, :, 2] + lightness * 2.55

        # Clamp values
        hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2], 0, 255)

        result_rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        result = np.concatenate([result_rgb, image[:, :, 3:4]], axis=2)
        return result


@register_filter("color_balance")
class ColorBalanceFilter(BaseFilter):
    """Adjust color balance (shadows, midtones, highlights)."""

    name = "Color Balance"
    description = "Adjust color balance for shadows, midtones, and highlights"
    category = "color"

    @classmethod
    def get_params_schema(cls):
        return [
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

    def apply(self, image: np.ndarray, red: int = 0, green: int = 0, blue: int = 0) -> np.ndarray:
        result = image.copy().astype(np.float32)

        # Apply color shifts
        result[:, :, 0] = np.clip(result[:, :, 0] + red * 2.55, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] + green * 2.55, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] + blue * 2.55, 0, 255)

        return result.astype(np.uint8)


@register_filter("gamma_correction")
class GammaCorrectionFilter(BaseFilter):
    """Apply gamma correction."""

    name = "Gamma Correction"
    description = "Adjust image gamma for exposure correction"
    category = "color"

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "gamma",
                "name": "Gamma",
                "type": "range",
                "min": 0.1,
                "max": 3.0,
                "step": 0.1,
                "default": 1.0,
            },
        ]

    def apply(self, image: np.ndarray, gamma: float = 1.0) -> np.ndarray:
        # Build lookup table
        inv_gamma = 1.0 / gamma
        table = np.array([(i / 255.0) ** inv_gamma * 255 for i in range(256)]).astype(np.uint8)

        result = image.copy()
        for c in range(3):
            result[:, :, c] = table[image[:, :, c]]

        return result


@register_filter("auto_contrast")
class AutoContrastFilter(BaseFilter):
    """Automatic contrast stretch."""

    name = "Auto Contrast"
    description = "Automatically stretch contrast for optimal range"
    category = "color"

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "clip_percent",
                "name": "Clip Percent",
                "type": "range",
                "min": 0.0,
                "max": 10.0,
                "step": 0.5,
                "default": 1.0,
            },
        ]

    def apply(self, image: np.ndarray, clip_percent: float = 1.0) -> np.ndarray:
        from skimage import exposure

        result = image.copy()
        for c in range(3):
            p_low, p_high = np.percentile(image[:, :, c], (clip_percent, 100 - clip_percent))
            result[:, :, c] = exposure.rescale_intensity(image[:, :, c], in_range=(p_low, p_high))

        return result


@register_filter("equalize_histogram")
class EqualizeHistogramFilter(BaseFilter):
    """Histogram equalization."""

    name = "Equalize Histogram"
    description = "Enhance contrast using histogram equalization"
    category = "color"

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "method",
                "name": "Method",
                "type": "select",
                "options": ["global", "adaptive"],
                "default": "global",
            },
        ]

    def apply(self, image: np.ndarray, method: str = "global") -> np.ndarray:
        import cv2

        result = image.copy()

        if method == "adaptive":
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            for c in range(3):
                result[:, :, c] = clahe.apply(image[:, :, c])
        else:
            # Global histogram equalization
            for c in range(3):
                result[:, :, c] = cv2.equalizeHist(image[:, :, c])

        return result


@register_filter("channel_mixer")
class ChannelMixerFilter(BaseFilter):
    """Mix color channels."""

    name = "Channel Mixer"
    description = "Mix and swap color channels"
    category = "color"

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

        result = image.copy()
        result[:, :, 0] = image[:, :, channel_map[red_channel]]
        result[:, :, 1] = image[:, :, channel_map[green_channel]]
        result[:, :, 2] = image[:, :, channel_map[blue_channel]]

        return result


@register_filter("vibrance")
class VibranceFilter(BaseFilter):
    """Adjust color vibrance."""

    name = "Vibrance"
    description = "Increase saturation of less-saturated colors"
    category = "color"

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "amount",
                "name": "Amount",
                "type": "range",
                "min": -100,
                "max": 100,
                "step": 1,
                "default": 25,
            },
        ]

    def apply(self, image: np.ndarray, amount: int = 25) -> np.ndarray:
        import cv2

        rgb = image[:, :, :3].astype(np.float32)
        hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)

        # Vibrance boosts less saturated colors more
        sat = hsv[:, :, 1] / 255.0
        boost = (1 - sat) * (amount / 100.0)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1 + boost), 0, 255)

        result_rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        result = np.concatenate([result_rgb, image[:, :, 3:4]], axis=2)
        return result


@register_filter("temperature")
class TemperatureFilter(BaseFilter):
    """Adjust color temperature (warm/cool)."""

    name = "Temperature"
    description = "Adjust color temperature (warm/cool)"
    category = "color"

    @classmethod
    def get_params_schema(cls):
        return [
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

    def apply(self, image: np.ndarray, temperature: int = 0) -> np.ndarray:
        result = image.copy().astype(np.float32)

        if temperature > 0:
            # Warm: increase red, decrease blue
            result[:, :, 0] = np.clip(result[:, :, 0] + temperature * 0.5, 0, 255)
            result[:, :, 2] = np.clip(result[:, :, 2] - temperature * 0.3, 0, 255)
        else:
            # Cool: decrease red, increase blue
            result[:, :, 0] = np.clip(result[:, :, 0] + temperature * 0.3, 0, 255)
            result[:, :, 2] = np.clip(result[:, :, 2] - temperature * 0.5, 0, 255)

        return result.astype(np.uint8)
