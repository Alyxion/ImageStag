"""Blur filters backed by imagestag_rust."""

from typing import ClassVar

import numpy as np
import imagestag_rust
from pydantic import Field

from .base import BaseFilter
from .registry import register_filter


@register_filter("gaussian_blur")
class GaussianBlurFilter(BaseFilter):
    """Gaussian blur filter."""

    filter_type: ClassVar[str] = "gaussian_blur"
    name: ClassVar[str] = "Gaussian Blur"
    description: ClassVar[str] = "Apply Gaussian blur to soften the image"
    category: ClassVar[str] = "blur"
    VERSION: ClassVar[int] = 1

    sigma: float = Field(default=3.0, ge=0.1, le=20.0,
                         json_schema_extra={"step": 0.1, "suffix": "px",
                                            "display_name": "Blur Radius"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.gaussian_blur_rgba(image, self.sigma)


@register_filter("box_blur")
class BoxBlurFilter(BaseFilter):
    """Box (uniform) blur filter."""

    filter_type: ClassVar[str] = "box_blur"
    name: ClassVar[str] = "Box Blur"
    description: ClassVar[str] = "Apply uniform box blur"
    category: ClassVar[str] = "blur"
    VERSION: ClassVar[int] = 1

    radius: int = Field(default=5, ge=1, le=50,
                        json_schema_extra={"step": 1, "suffix": "px",
                                           "display_name": "Radius"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.box_blur_rgba(image, int(self.radius))


@register_filter("median_blur")
class MedianBlurFilter(BaseFilter):
    """Median blur filter - good for noise reduction."""

    filter_type: ClassVar[str] = "median_blur"
    name: ClassVar[str] = "Median Blur"
    description: ClassVar[str] = "Apply median filter to reduce noise while preserving edges"
    category: ClassVar[str] = "blur"
    VERSION: ClassVar[int] = 1

    radius: int = Field(default=3, ge=1, le=21,
                        json_schema_extra={"step": 1, "suffix": "px",
                                           "display_name": "Radius"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.median(image, int(self.radius))


@register_filter("motion_blur")
class MotionBlurFilter(BaseFilter):
    """Motion blur filter."""

    filter_type: ClassVar[str] = "motion_blur"
    name: ClassVar[str] = "Motion Blur"
    description: ClassVar[str] = "Apply directional motion blur effect"
    category: ClassVar[str] = "blur"
    VERSION: ClassVar[int] = 1

    distance: float = Field(default=15.0, ge=3.0, le=50.0,
                            json_schema_extra={"step": 1, "suffix": "px",
                                               "display_name": "Blur Length"})
    angle: float = Field(default=0.0, ge=0.0, le=360.0,
                         json_schema_extra={"step": 1, "suffix": "\u00b0",
                                            "display_name": "Angle"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.motion_blur(image, float(self.angle), float(self.distance))
