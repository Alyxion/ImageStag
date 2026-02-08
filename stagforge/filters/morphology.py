"""Morphological operation filters."""

import numpy as np

import imagestag_rust
from .base import BaseFilter
from .registry import register_filter


@register_filter("morphology_op")
class MorphologyOpFilter(BaseFilter):
    """Combined morphological operations with operation selection."""

    name = "Morphology"
    description = "Apply morphological operations"
    category = "morphology"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "operation",
                "name": "Operation",
                "type": "select",
                "options": ["dilate", "erode", "open", "close", "gradient", "tophat", "blackhat"],
                "default": "dilate",
            },
            {
                "id": "radius",
                "name": "Radius",
                "type": "range",
                "min": 1,
                "max": 20,
                "step": 1,
                "default": 1,
                "suffix": "px",
            },
        ]

    def apply(self, image: np.ndarray, operation: str = "dilate", radius: int = 1, **kwargs) -> np.ndarray:
        r = int(radius)
        ops = {
            "dilate": lambda: imagestag_rust.dilate(image, r),
            "erode": lambda: imagestag_rust.erode(image, r),
            "open": lambda: imagestag_rust.morphology_open(image, r),
            "close": lambda: imagestag_rust.morphology_close(image, r),
            "gradient": lambda: imagestag_rust.morphology_gradient(image, r),
            "tophat": lambda: imagestag_rust.tophat(image, r),
            "blackhat": lambda: imagestag_rust.blackhat(image, r),
        }
        return ops.get(operation, ops["dilate"])()
