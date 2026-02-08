"""Artistic effect filters."""

import numpy as np

import imagestag_rust
from .base import BaseFilter
from .registry import register_filter


@register_filter("emboss")
class EmbossFilter(BaseFilter):
    """Emboss effect filter."""

    name = "Emboss"
    description = "Create an embossed 3D effect"
    category = "artistic"
    version = 2

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "angle",
                "name": "Angle",
                "type": "range",
                "min": 0,
                "max": 360,
                "step": 1,
                "default": 135,
                "suffix": "°",
            },
            {
                "id": "depth",
                "name": "Depth",
                "type": "range",
                "min": 0.1,
                "max": 5.0,
                "step": 0.1,
                "default": 1.0,
            },
        ]

    def apply(self, image: np.ndarray, angle: float = 135.0, depth: float = 1.0, **kwargs) -> np.ndarray:
        # Support legacy "direction" param by mapping to angle
        direction = kwargs.get("direction")
        if direction is not None:
            direction_to_angle = {
                "top_left": 135,
                "top": 90,
                "top_right": 45,
                "left": 180,
                "right": 0,
                "bottom_left": 225,
                "bottom": 270,
                "bottom_right": 315,
            }
            angle = float(direction_to_angle.get(direction, 135))

        # Support legacy "strength" param by mapping to depth
        strength = kwargs.get("strength")
        if strength is not None:
            depth = float(strength)

        return imagestag_rust.emboss(image, float(angle), float(depth))


@register_filter("pencil_sketch")
class PencilSketchFilter(BaseFilter):
    """Pencil sketch effect (Python-only composite filter)."""

    name = "Pencil Sketch"
    description = "Convert to pencil sketch style"
    category = "artistic"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "sigma_s",
                "name": "Smoothness",
                "type": "range",
                "min": 10,
                "max": 200,
                "step": 10,
                "default": 60,
            },
            {
                "id": "sigma_r",
                "name": "Edge Strength",
                "type": "range",
                "min": 1,
                "max": 100,
                "step": 1,
                "default": 35,
                "suffix": "%",
            },
            {
                "id": "shade_factor",
                "name": "Shade Factor",
                "type": "range",
                "min": 0,
                "max": 100,
                "step": 1,
                "default": 50,
                "suffix": "%",
            },
        ]

    def apply(self, image: np.ndarray, sigma_s: int = 60, sigma_r: float = 35, shade_factor: float = 50) -> np.ndarray:
        return imagestag_rust.pencil_sketch(image, float(sigma_s), float(shade_factor))


@register_filter("pixelate")
class PixelateFilter(BaseFilter):
    """Pixelation effect."""

    name = "Pixelate"
    description = "Apply pixelation/mosaic effect"
    category = "artistic"
    version = 2

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "block_size",
                "name": "Block Size",
                "type": "range",
                "min": 2,
                "max": 50,
                "step": 1,
                "default": 10,
                "suffix": "px",
            },
        ]

    def apply(self, image: np.ndarray, block_size: int = 10) -> np.ndarray:
        return imagestag_rust.pixelate(image, int(block_size))


@register_filter("vignette")
class VignetteFilter(BaseFilter):
    """Vignette effect (darkened corners)."""

    name = "Vignette"
    description = "Add darkened corners vignette effect"
    category = "artistic"
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
                "default": 40,
                "suffix": "%",
            },
        ]

    def apply(self, image: np.ndarray, amount: float = 40, **kwargs) -> np.ndarray:
        # Support legacy params by mapping (strength, radius) to amount
        strength = kwargs.get("strength")
        if strength is not None:
            amount = float(strength)
            return imagestag_rust.vignette(image, amount)

        return imagestag_rust.vignette(image, float(amount) * 0.02)


@register_filter("solarize")
class SolarizeFilter(BaseFilter):
    """Solarize effect (invert tones above threshold)."""

    name = "Solarize"
    description = "Invert tones above a brightness threshold"
    category = "artistic"
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
        ]

    def apply(self, image: np.ndarray, threshold: int = 128) -> np.ndarray:
        return imagestag_rust.solarize(image, int(threshold))
