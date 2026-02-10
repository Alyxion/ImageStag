"""Threshold filters."""

from typing import ClassVar

import numpy as np
import imagestag_rust
from pydantic import Field

from .base import BaseFilter
from .registry import register_filter


@register_filter("posterize")
class PosterizeFilter(BaseFilter):
    """Reduce number of colors (posterization)."""

    filter_type: ClassVar[str] = "posterize"
    name: ClassVar[str] = "Posterize"
    description: ClassVar[str] = "Reduce the number of color levels"
    category: ClassVar[str] = "artistic"
    VERSION: ClassVar[int] = 2

    levels: int = Field(default=4, ge=2, le=32,
                        json_schema_extra={"step": 1,
                                           "display_name": "Color Levels"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.posterize(image, int(self.levels))
