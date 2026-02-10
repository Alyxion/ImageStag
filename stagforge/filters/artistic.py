"""Artistic effect filters."""

from typing import ClassVar

import numpy as np
import imagestag_rust
from pydantic import Field

from .base import BaseFilter
from .registry import register_filter


@register_filter("emboss")
class EmbossFilter(BaseFilter):
    """Emboss effect filter."""

    filter_type: ClassVar[str] = "emboss"
    name: ClassVar[str] = "Emboss"
    description: ClassVar[str] = "Create an embossed 3D effect"
    category: ClassVar[str] = "artistic"
    VERSION: ClassVar[int] = 2

    angle: float = Field(default=135.0, ge=0.0, le=360.0,
                         json_schema_extra={"step": 1, "suffix": "\u00b0",
                                            "display_name": "Angle"})
    depth: float = Field(default=1.0, ge=0.1, le=5.0,
                         json_schema_extra={"step": 0.1,
                                            "display_name": "Depth"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.emboss(image, float(self.angle), float(self.depth))


@register_filter("pencil_sketch")
class PencilSketchFilter(BaseFilter):
    """Pencil sketch effect (Python-only composite filter)."""

    filter_type: ClassVar[str] = "pencil_sketch"
    name: ClassVar[str] = "Pencil Sketch"
    description: ClassVar[str] = "Convert to pencil sketch style"
    category: ClassVar[str] = "artistic"
    VERSION: ClassVar[int] = 1

    sigma_s: int = Field(default=60, ge=10, le=200,
                         json_schema_extra={"step": 10,
                                            "display_name": "Smoothness"})
    sigma_r: int = Field(default=35, ge=1, le=100,
                         json_schema_extra={"step": 1, "suffix": "%",
                                            "display_name": "Edge Strength"})
    shade_factor: int = Field(default=50, ge=0, le=100,
                              json_schema_extra={"step": 1, "suffix": "%",
                                                 "display_name": "Shade Factor"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.pencil_sketch(image, float(self.sigma_s),
                                            float(self.shade_factor))


@register_filter("pixelate")
class PixelateFilter(BaseFilter):
    """Pixelation effect."""

    filter_type: ClassVar[str] = "pixelate"
    name: ClassVar[str] = "Pixelate"
    description: ClassVar[str] = "Apply pixelation/mosaic effect"
    category: ClassVar[str] = "artistic"
    VERSION: ClassVar[int] = 2

    block_size: int = Field(default=10, ge=2, le=50,
                            json_schema_extra={"step": 1, "suffix": "px",
                                               "display_name": "Block Size"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.pixelate(image, int(self.block_size))


@register_filter("vignette")
class VignetteFilter(BaseFilter):
    """Vignette effect (darkened corners)."""

    filter_type: ClassVar[str] = "vignette"
    name: ClassVar[str] = "Vignette"
    description: ClassVar[str] = "Add darkened corners vignette effect"
    category: ClassVar[str] = "artistic"
    VERSION: ClassVar[int] = 2

    amount: float = Field(default=40.0, ge=0.0, le=100.0,
                          json_schema_extra={"step": 1, "suffix": "%",
                                             "display_name": "Amount"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.vignette(image, float(self.amount) * 0.02)


@register_filter("solarize")
class SolarizeFilter(BaseFilter):
    """Solarize effect (invert tones above threshold)."""

    filter_type: ClassVar[str] = "solarize"
    name: ClassVar[str] = "Solarize"
    description: ClassVar[str] = "Invert tones above a brightness threshold"
    category: ClassVar[str] = "artistic"
    VERSION: ClassVar[int] = 1

    threshold: int = Field(default=128, ge=0, le=255,
                           json_schema_extra={"step": 1,
                                              "display_name": "Threshold"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        return imagestag_rust.solarize(image, int(self.threshold))
