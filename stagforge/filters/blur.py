"""Blur filters backed by imagestag_rust."""

import numpy as np

import imagestag_rust

from .base import BaseFilter
from .registry import register_filter


@register_filter("gaussian_blur")
class GaussianBlurFilter(BaseFilter):
    """Gaussian blur filter."""

    name = "Gaussian Blur"
    description = "Apply Gaussian blur to soften the image"
    category = "blur"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "sigma",
                "name": "Blur Radius",
                "type": "range",
                "min": 0.1,
                "max": 20.0,
                "step": 0.1,
                "default": 3.0,
                "suffix": "px",
            }
        ]

    def apply(self, image: np.ndarray, sigma: float = 3.0) -> np.ndarray:
        return imagestag_rust.gaussian_blur_rgba(image, sigma)


@register_filter("box_blur")
class BoxBlurFilter(BaseFilter):
    """Box (uniform) blur filter."""

    name = "Box Blur"
    description = "Apply uniform box blur"
    category = "blur"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "radius",
                "name": "Radius",
                "type": "range",
                "min": 1,
                "max": 50,
                "step": 1,
                "default": 5,
                "suffix": "px",
            }
        ]

    def apply(self, image: np.ndarray, radius: int = 5) -> np.ndarray:
        return imagestag_rust.box_blur_rgba(image, int(radius))


@register_filter("median_blur")
class MedianBlurFilter(BaseFilter):
    """Median blur filter - good for noise reduction."""

    name = "Median Blur"
    description = "Apply median filter to reduce noise while preserving edges"
    category = "blur"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "radius",
                "name": "Radius",
                "type": "range",
                "min": 1,
                "max": 21,
                "step": 1,
                "default": 3,
                "suffix": "px",
            }
        ]

    def apply(self, image: np.ndarray, radius: int = 3) -> np.ndarray:
        return imagestag_rust.median(image, int(radius))


@register_filter("motion_blur")
class MotionBlurFilter(BaseFilter):
    """Motion blur filter."""

    name = "Motion Blur"
    description = "Apply directional motion blur effect"
    category = "blur"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "distance",
                "name": "Blur Length",
                "type": "range",
                "min": 3,
                "max": 50,
                "step": 1,
                "default": 15,
                "suffix": "px",
            },
            {
                "id": "angle",
                "name": "Angle",
                "type": "range",
                "min": 0,
                "max": 360,
                "step": 1,
                "default": 0,
                "suffix": "°",
            },
        ]

    def apply(self, image: np.ndarray, distance: float = 15.0, angle: float = 0.0) -> np.ndarray:
        return imagestag_rust.motion_blur(image, float(angle), float(distance))
