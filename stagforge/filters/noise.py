"""Noise and denoising filters."""

from typing import ClassVar

import numpy as np
import imagestag_rust
from pydantic import Field

from .base import BaseFilter
from .registry import register_filter


@register_filter("add_noise")
class AddNoiseFilter(BaseFilter):
    """Add noise to image."""

    filter_type: ClassVar[str] = "add_noise"
    name: ClassVar[str] = "Add Noise"
    description: ClassVar[str] = "Add random noise to the image"
    category: ClassVar[str] = "noise"
    VERSION: ClassVar[int] = 2

    amount: int = Field(default=20, ge=0, le=100,
                        json_schema_extra={"step": 1, "suffix": "%",
                                           "display_name": "Amount"})
    gaussian: bool = Field(default=True,
                           json_schema_extra={"display_name": "Gaussian"})
    monochrome: bool = Field(default=False,
                             json_schema_extra={"display_name": "Monochrome"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        strength = self.amount / 100.0
        return imagestag_rust.add_noise(image, strength, self.gaussian,
                                        self.monochrome, 0)


@register_filter("denoise")
class DenoiseFilter(BaseFilter):
    """Remove noise using denoising algorithm."""

    filter_type: ClassVar[str] = "denoise"
    name: ClassVar[str] = "Denoise"
    description: ClassVar[str] = "Remove noise from the image"
    category: ClassVar[str] = "noise"
    VERSION: ClassVar[int] = 2

    strength: int = Field(default=33, ge=0, le=100,
                          json_schema_extra={"step": 1, "suffix": "%",
                                             "display_name": "Strength"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.denoise(image, self.strength / 100.0)
