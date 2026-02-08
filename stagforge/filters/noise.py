"""Noise and denoising filters."""

import numpy as np
import imagestag_rust

from .base import BaseFilter
from .registry import register_filter


@register_filter("add_noise")
class AddNoiseFilter(BaseFilter):
    """Add noise to image."""

    name = "Add Noise"
    description = "Add random noise to the image"
    category = "noise"
    version = 2

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "amount",
                "name": "Amount",
                "type": "range",
                "min": 0,
                "max": 100,
                "step": 1,
                "default": 20,
                "suffix": "%",
            },
            {
                "id": "gaussian",
                "name": "Gaussian",
                "type": "checkbox",
                "default": True,
            },
            {
                "id": "monochrome",
                "name": "Monochrome",
                "type": "checkbox",
                "default": False,
            },
        ]

    def apply(self, image: np.ndarray, amount: int = 20, gaussian: bool = True, monochrome: bool = False) -> np.ndarray:
        strength = amount / 100.0
        return imagestag_rust.add_noise(image, strength, gaussian, monochrome, 0)


@register_filter("denoise")
class DenoiseFilter(BaseFilter):
    """Remove noise using denoising algorithm."""

    name = "Denoise"
    description = "Remove noise from the image"
    category = "noise"
    version = 2

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "strength",
                "name": "Strength",
                "type": "range",
                "min": 0,
                "max": 100,
                "step": 1,
                "default": 33,
                "suffix": "%",
            },
        ]

    def apply(self, image: np.ndarray, strength: int = 33) -> np.ndarray:
        return imagestag_rust.denoise(image, strength / 100.0)
