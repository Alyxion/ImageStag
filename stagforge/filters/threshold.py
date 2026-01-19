"""Threshold filters."""

import numpy as np
import cv2

from .base import BaseFilter
from .registry import register_filter


@register_filter("binary_threshold")
class BinaryThresholdFilter(BaseFilter):
    """Simple binary threshold."""

    name = "Binary Threshold"
    description = "Convert to black and white using a threshold"
    category = "threshold"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "threshold",
                "name": "Threshold",
                "type": "range",
                "min": 0,
                "max": 255,
                "step": 1,
                "default": 128,
            },
            {
                "id": "invert",
                "name": "Invert",
                "type": "select",
                "options": ["false", "true"],
                "default": "false",
            },
        ]

    def apply(self, image: np.ndarray, threshold: int = 128, invert: str = "false") -> np.ndarray:
        gray = np.mean(image[:, :, :3], axis=2).astype(np.uint8)

        thresh_type = cv2.THRESH_BINARY_INV if invert == "true" else cv2.THRESH_BINARY
        _, binary = cv2.threshold(gray, threshold, 255, thresh_type)

        result = np.stack([binary, binary, binary, image[:, :, 3]], axis=2)
        return result


@register_filter("otsu_threshold")
class OtsuThresholdFilter(BaseFilter):
    """Otsu's automatic thresholding."""

    name = "Otsu Threshold"
    description = "Automatically determine optimal threshold (Otsu's method)"
    category = "threshold"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "invert",
                "name": "Invert",
                "type": "select",
                "options": ["false", "true"],
                "default": "false",
            },
        ]

    def apply(self, image: np.ndarray, invert: str = "false") -> np.ndarray:
        gray = np.mean(image[:, :, :3], axis=2).astype(np.uint8)

        thresh_type = cv2.THRESH_BINARY_INV if invert == "true" else cv2.THRESH_BINARY
        _, binary = cv2.threshold(gray, 0, 255, thresh_type | cv2.THRESH_OTSU)

        result = np.stack([binary, binary, binary, image[:, :, 3]], axis=2)
        return result


@register_filter("adaptive_threshold")
class AdaptiveThresholdFilter(BaseFilter):
    """Adaptive thresholding for varying lighting."""

    name = "Adaptive Threshold"
    description = "Threshold that adapts to local image regions"
    category = "threshold"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "method",
                "name": "Method",
                "type": "select",
                "options": ["mean", "gaussian"],
                "default": "gaussian",
            },
            {
                "id": "block_size",
                "name": "Block Size",
                "type": "range",
                "min": 3,
                "max": 99,
                "step": 2,
                "default": 11,
            },
            {
                "id": "c",
                "name": "Constant (C)",
                "type": "range",
                "min": -20,
                "max": 20,
                "step": 1,
                "default": 2,
            },
            {
                "id": "invert",
                "name": "Invert",
                "type": "select",
                "options": ["false", "true"],
                "default": "false",
            },
        ]

    def apply(self, image: np.ndarray, method: str = "gaussian", block_size: int = 11, c: int = 2, invert: str = "false") -> np.ndarray:
        gray = np.mean(image[:, :, :3], axis=2).astype(np.uint8)

        # Ensure block_size is odd
        block_size = block_size if block_size % 2 == 1 else block_size + 1

        adaptive_method = cv2.ADAPTIVE_THRESH_GAUSSIAN_C if method == "gaussian" else cv2.ADAPTIVE_THRESH_MEAN_C
        thresh_type = cv2.THRESH_BINARY_INV if invert == "true" else cv2.THRESH_BINARY

        binary = cv2.adaptiveThreshold(gray, 255, adaptive_method, thresh_type, block_size, c)

        result = np.stack([binary, binary, binary, image[:, :, 3]], axis=2)
        return result


@register_filter("color_threshold")
class ColorThresholdFilter(BaseFilter):
    """Threshold based on color range in HSV space."""

    name = "Color Threshold"
    description = "Select pixels within a color range (HSV)"
    category = "threshold"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "hue_min",
                "name": "Hue Min",
                "type": "range",
                "min": 0,
                "max": 180,
                "step": 1,
                "default": 0,
            },
            {
                "id": "hue_max",
                "name": "Hue Max",
                "type": "range",
                "min": 0,
                "max": 180,
                "step": 1,
                "default": 180,
            },
            {
                "id": "sat_min",
                "name": "Saturation Min",
                "type": "range",
                "min": 0,
                "max": 255,
                "step": 1,
                "default": 50,
            },
            {
                "id": "sat_max",
                "name": "Saturation Max",
                "type": "range",
                "min": 0,
                "max": 255,
                "step": 1,
                "default": 255,
            },
            {
                "id": "val_min",
                "name": "Value Min",
                "type": "range",
                "min": 0,
                "max": 255,
                "step": 1,
                "default": 50,
            },
            {
                "id": "val_max",
                "name": "Value Max",
                "type": "range",
                "min": 0,
                "max": 255,
                "step": 1,
                "default": 255,
            },
        ]

    def apply(
        self,
        image: np.ndarray,
        hue_min: int = 0,
        hue_max: int = 180,
        sat_min: int = 50,
        sat_max: int = 255,
        val_min: int = 50,
        val_max: int = 255,
    ) -> np.ndarray:
        # Convert to HSV
        rgb = image[:, :, :3]
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

        # Create mask
        lower = np.array([hue_min, sat_min, val_min])
        upper = np.array([hue_max, sat_max, val_max])
        mask = cv2.inRange(hsv, lower, upper)

        result = np.stack([mask, mask, mask, image[:, :, 3]], axis=2)
        return result


@register_filter("posterize")
class PosterizeFilter(BaseFilter):
    """Reduce number of colors (posterization)."""

    name = "Posterize"
    description = "Reduce the number of color levels"
    category = "threshold"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "levels",
                "name": "Color Levels",
                "type": "range",
                "min": 2,
                "max": 32,
                "step": 1,
                "default": 4,
            },
        ]

    def apply(self, image: np.ndarray, levels: int = 4) -> np.ndarray:
        # Calculate the size of each color bin
        divisor = 256 // levels
        if divisor < 1:
            divisor = 1

        result = image.copy()
        for c in range(3):
            # Quantize each channel
            result[:, :, c] = (image[:, :, c] // divisor) * divisor + divisor // 2
            result[:, :, c] = np.clip(result[:, :, c], 0, 255)

        return result
