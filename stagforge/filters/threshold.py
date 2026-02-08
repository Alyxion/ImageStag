"""Threshold filters."""

import numpy as np

import imagestag_rust
from .base import BaseFilter
from .registry import register_filter



@register_filter("posterize")
class PosterizeFilter(BaseFilter):
    """Reduce number of colors (posterization)."""

    name = "Posterize"
    description = "Reduce the number of color levels"
    category = "artistic"
    version = 2

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
        return imagestag_rust.posterize(image, int(levels))
