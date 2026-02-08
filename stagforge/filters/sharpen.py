"""Sharpen filters."""

import numpy as np

import imagestag_rust
from .base import BaseFilter
from .registry import register_filter


@register_filter("unsharp_mask")
class UnsharpMaskFilter(BaseFilter):
    """Unsharp mask sharpening filter."""

    name = "Unsharp Mask"
    description = "Sharpen image using unsharp masking"
    category = "sharpen"
    version = 2

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "radius",
                "name": "Radius",
                "type": "range",
                "min": 0.1,
                "max": 10.0,
                "step": 0.1,
                "default": 1.0,
                "suffix": "px",
            },
            {
                "id": "amount",
                "name": "Amount",
                "type": "range",
                "min": 0.1,
                "max": 5.0,
                "step": 0.1,
                "default": 1.0,
            },
            {
                "id": "threshold",
                "name": "Threshold",
                "type": "range",
                "min": 0,
                "max": 255,
                "step": 1,
                "default": 0,
            },
        ]

    def apply(self, image: np.ndarray, amount: float = 1.0, radius: float = 1.0, threshold: int = 0) -> np.ndarray:
        return imagestag_rust.unsharp_mask(image, float(amount), float(radius), int(threshold))


@register_filter("sharpen")
class SharpenFilter(BaseFilter):
    """Simple convolution sharpening."""

    name = "Sharpen"
    description = "Sharpen image using convolution"
    category = "sharpen"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "amount",
                "name": "Amount",
                "type": "range",
                "min": 0.0,
                "max": 5.0,
                "step": 0.1,
                "default": 0.5,
            },
        ]

    def apply(self, image: np.ndarray, amount: float = 0.5) -> np.ndarray:
        return imagestag_rust.sharpen(image, float(amount))


@register_filter("high_pass")
class HighPassFilter(BaseFilter):
    """High pass filter for detail extraction."""

    name = "High Pass"
    description = "Extract high-frequency detail from image"
    category = "sharpen"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "radius",
                "name": "Radius",
                "type": "range",
                "min": 1.0,
                "max": 50.0,
                "step": 1.0,
                "default": 3.0,
                "suffix": "px",
            },
        ]

    def apply(self, image: np.ndarray, radius: float = 3.0) -> np.ndarray:
        return imagestag_rust.high_pass(image, float(radius))
