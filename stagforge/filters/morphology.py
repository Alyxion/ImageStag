"""Morphological operation filters."""

from typing import ClassVar

import numpy as np
import imagestag_rust
from pydantic import Field

from .base import BaseFilter
from .registry import register_filter


@register_filter("morphology_op")
class MorphologyOpFilter(BaseFilter):
    """Combined morphological operations with operation selection."""

    filter_type: ClassVar[str] = "morphology_op"
    name: ClassVar[str] = "Morphology"
    description: ClassVar[str] = "Apply morphological operations"
    category: ClassVar[str] = "morphology"
    VERSION: ClassVar[int] = 1

    operation: str = Field(
        default="dilate",
        json_schema_extra={
            "options": ["dilate", "erode", "open", "close", "gradient", "tophat", "blackhat"],
            "display_name": "Operation",
        },
    )
    radius: int = Field(default=1, ge=1, le=20,
                        json_schema_extra={"step": 1, "suffix": "px",
                                           "display_name": "Radius"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        r = int(self.radius)
        ops = {
            "dilate": lambda: imagestag_rust.dilate(image, r),
            "erode": lambda: imagestag_rust.erode(image, r),
            "open": lambda: imagestag_rust.morphology_open(image, r),
            "close": lambda: imagestag_rust.morphology_close(image, r),
            "gradient": lambda: imagestag_rust.morphology_gradient(image, r),
            "tophat": lambda: imagestag_rust.tophat(image, r),
            "blackhat": lambda: imagestag_rust.blackhat(image, r),
        }
        return ops.get(self.operation, ops["dilate"])()
