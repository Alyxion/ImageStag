"""Sharpen filters."""

from typing import ClassVar

import numpy as np
import imagestag_rust
from pydantic import Field

from .base import BaseFilter
from .registry import register_filter


@register_filter("unsharp_mask")
class UnsharpMaskFilter(BaseFilter):
    """Unsharp mask sharpening filter."""

    filter_type: ClassVar[str] = "unsharp_mask"
    name: ClassVar[str] = "Unsharp Mask"
    description: ClassVar[str] = "Sharpen image using unsharp masking"
    category: ClassVar[str] = "sharpen"
    VERSION: ClassVar[int] = 2

    radius: float = Field(default=1.0, ge=0.1, le=10.0,
                          json_schema_extra={"step": 0.1, "suffix": "px",
                                             "display_name": "Radius"})
    amount: float = Field(default=1.0, ge=0.1, le=5.0,
                          json_schema_extra={"step": 0.1,
                                             "display_name": "Amount"})
    threshold: int = Field(default=0, ge=0, le=255,
                           json_schema_extra={"step": 1,
                                              "display_name": "Threshold"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.unsharp_mask(image, float(self.amount),
                                           float(self.radius), int(self.threshold))


@register_filter("sharpen")
class SharpenFilter(BaseFilter):
    """Simple convolution sharpening."""

    filter_type: ClassVar[str] = "sharpen"
    name: ClassVar[str] = "Sharpen"
    description: ClassVar[str] = "Sharpen image using convolution"
    category: ClassVar[str] = "sharpen"
    VERSION: ClassVar[int] = 1

    amount: float = Field(default=0.5, ge=0.0, le=5.0,
                          json_schema_extra={"step": 0.1,
                                             "display_name": "Amount"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.sharpen(image, float(self.amount))


@register_filter("high_pass")
class HighPassFilter(BaseFilter):
    """High pass filter for detail extraction."""

    filter_type: ClassVar[str] = "high_pass"
    name: ClassVar[str] = "High Pass"
    description: ClassVar[str] = "Extract high-frequency detail from image"
    category: ClassVar[str] = "sharpen"
    VERSION: ClassVar[int] = 1

    radius: float = Field(default=3.0, ge=1.0, le=50.0,
                          json_schema_extra={"step": 1.0, "suffix": "px",
                                             "display_name": "Radius"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.high_pass(image, float(self.radius))
