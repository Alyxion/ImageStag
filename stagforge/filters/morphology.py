"""Morphological operation filters."""

import numpy as np
import cv2

from .base import BaseFilter
from .registry import register_filter


@register_filter("erode")
class ErodeFilter(BaseFilter):
    """Erosion morphological filter."""

    name = "Erode"
    description = "Erode/shrink bright regions"
    category = "morphology"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "kernel_size",
                "name": "Kernel Size",
                "type": "range",
                "min": 1,
                "max": 21,
                "step": 2,
                "default": 3,
            },
            {
                "id": "iterations",
                "name": "Iterations",
                "type": "range",
                "min": 1,
                "max": 10,
                "step": 1,
                "default": 1,
            },
            {
                "id": "shape",
                "name": "Kernel Shape",
                "type": "select",
                "options": ["rect", "ellipse", "cross"],
                "default": "rect",
            },
        ]

    def apply(self, image: np.ndarray, kernel_size: int = 3, iterations: int = 1, shape: str = "rect") -> np.ndarray:
        shapes = {
            "rect": cv2.MORPH_RECT,
            "ellipse": cv2.MORPH_ELLIPSE,
            "cross": cv2.MORPH_CROSS,
        }
        kernel = cv2.getStructuringElement(shapes.get(shape, cv2.MORPH_RECT), (kernel_size, kernel_size))

        result = image.copy()
        result[:, :, :3] = cv2.erode(image[:, :, :3], kernel, iterations=iterations)
        return result


@register_filter("dilate")
class DilateFilter(BaseFilter):
    """Dilation morphological filter."""

    name = "Dilate"
    description = "Dilate/expand bright regions"
    category = "morphology"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "kernel_size",
                "name": "Kernel Size",
                "type": "range",
                "min": 1,
                "max": 21,
                "step": 2,
                "default": 3,
            },
            {
                "id": "iterations",
                "name": "Iterations",
                "type": "range",
                "min": 1,
                "max": 10,
                "step": 1,
                "default": 1,
            },
            {
                "id": "shape",
                "name": "Kernel Shape",
                "type": "select",
                "options": ["rect", "ellipse", "cross"],
                "default": "rect",
            },
        ]

    def apply(self, image: np.ndarray, kernel_size: int = 3, iterations: int = 1, shape: str = "rect") -> np.ndarray:
        shapes = {
            "rect": cv2.MORPH_RECT,
            "ellipse": cv2.MORPH_ELLIPSE,
            "cross": cv2.MORPH_CROSS,
        }
        kernel = cv2.getStructuringElement(shapes.get(shape, cv2.MORPH_RECT), (kernel_size, kernel_size))

        result = image.copy()
        result[:, :, :3] = cv2.dilate(image[:, :, :3], kernel, iterations=iterations)
        return result


@register_filter("morphology_open")
class OpenFilter(BaseFilter):
    """Opening morphological filter (erosion then dilation)."""

    name = "Open"
    description = "Remove small bright spots (erosion then dilation)"
    category = "morphology"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "kernel_size",
                "name": "Kernel Size",
                "type": "range",
                "min": 1,
                "max": 21,
                "step": 2,
                "default": 3,
            },
            {
                "id": "shape",
                "name": "Kernel Shape",
                "type": "select",
                "options": ["rect", "ellipse", "cross"],
                "default": "rect",
            },
        ]

    def apply(self, image: np.ndarray, kernel_size: int = 3, shape: str = "rect") -> np.ndarray:
        shapes = {
            "rect": cv2.MORPH_RECT,
            "ellipse": cv2.MORPH_ELLIPSE,
            "cross": cv2.MORPH_CROSS,
        }
        kernel = cv2.getStructuringElement(shapes.get(shape, cv2.MORPH_RECT), (kernel_size, kernel_size))

        result = image.copy()
        result[:, :, :3] = cv2.morphologyEx(image[:, :, :3], cv2.MORPH_OPEN, kernel)
        return result


@register_filter("morphology_close")
class CloseFilter(BaseFilter):
    """Closing morphological filter (dilation then erosion)."""

    name = "Close"
    description = "Fill small dark holes (dilation then erosion)"
    category = "morphology"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "kernel_size",
                "name": "Kernel Size",
                "type": "range",
                "min": 1,
                "max": 21,
                "step": 2,
                "default": 3,
            },
            {
                "id": "shape",
                "name": "Kernel Shape",
                "type": "select",
                "options": ["rect", "ellipse", "cross"],
                "default": "rect",
            },
        ]

    def apply(self, image: np.ndarray, kernel_size: int = 3, shape: str = "rect") -> np.ndarray:
        shapes = {
            "rect": cv2.MORPH_RECT,
            "ellipse": cv2.MORPH_ELLIPSE,
            "cross": cv2.MORPH_CROSS,
        }
        kernel = cv2.getStructuringElement(shapes.get(shape, cv2.MORPH_RECT), (kernel_size, kernel_size))

        result = image.copy()
        result[:, :, :3] = cv2.morphologyEx(image[:, :, :3], cv2.MORPH_CLOSE, kernel)
        return result


@register_filter("morphology_gradient")
class MorphologyGradientFilter(BaseFilter):
    """Morphological gradient (difference between dilation and erosion)."""

    name = "Morphological Gradient"
    description = "Extract edges using morphological gradient"
    category = "morphology"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "kernel_size",
                "name": "Kernel Size",
                "type": "range",
                "min": 1,
                "max": 21,
                "step": 2,
                "default": 3,
            },
        ]

    def apply(self, image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

        result = image.copy()
        result[:, :, :3] = cv2.morphologyEx(image[:, :, :3], cv2.MORPH_GRADIENT, kernel)
        return result


@register_filter("tophat")
class TopHatFilter(BaseFilter):
    """Top hat transform (difference between input and opening)."""

    name = "Top Hat"
    description = "Extract bright regions smaller than the kernel"
    category = "morphology"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "kernel_size",
                "name": "Kernel Size",
                "type": "range",
                "min": 3,
                "max": 51,
                "step": 2,
                "default": 9,
            },
        ]

    def apply(self, image: np.ndarray, kernel_size: int = 9) -> np.ndarray:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

        result = image.copy()
        result[:, :, :3] = cv2.morphologyEx(image[:, :, :3], cv2.MORPH_TOPHAT, kernel)
        return result


@register_filter("blackhat")
class BlackHatFilter(BaseFilter):
    """Black hat transform (difference between closing and input)."""

    name = "Black Hat"
    description = "Extract dark regions smaller than the kernel"
    category = "morphology"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "kernel_size",
                "name": "Kernel Size",
                "type": "range",
                "min": 3,
                "max": 51,
                "step": 2,
                "default": 9,
            },
        ]

    def apply(self, image: np.ndarray, kernel_size: int = 9) -> np.ndarray:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

        result = image.copy()
        result[:, :, :3] = cv2.morphologyEx(image[:, :, :3], cv2.MORPH_BLACKHAT, kernel)
        return result
