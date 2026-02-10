"""Edge detection filters."""

from typing import ClassVar

import numpy as np
import imagestag_rust
from pydantic import Field

from .base import BaseFilter
from .registry import register_filter


@register_filter("edge_detect")
class EdgeDetectFilter(BaseFilter):
    """Combined edge detection with method selection."""

    filter_type: ClassVar[str] = "edge_detect"
    name: ClassVar[str] = "Edge Detection"
    description: ClassVar[str] = "Detect edges using various methods"
    category: ClassVar[str] = "edge"
    VERSION: ClassVar[int] = 2

    method: str = Field(default="sobel",
                        json_schema_extra={"options": ["sobel", "laplacian"],
                                           "display_name": "Method"})
    direction: str = Field(default="both",
                           json_schema_extra={"options": ["both", "horizontal", "vertical"],
                                              "display_name": "Direction",
                                              "visible_when": {"method": ["sobel"]}})
    kernel_size: str = Field(default="3",
                             json_schema_extra={"options": ["3", "5", "7"],
                                                "display_name": "Kernel Size"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        if self.method == "laplacian":
            return imagestag_rust.laplacian(image, int(self.kernel_size))
        else:
            direction_map = {"both": "both", "horizontal": "h", "vertical": "v"}
            return imagestag_rust.sobel(
                image, direction_map.get(self.direction, "both"), int(self.kernel_size)
            )


@register_filter("find_contours")
class FindContoursFilter(BaseFilter):
    """Find and draw contours using Canny edge detection."""

    filter_type: ClassVar[str] = "find_contours"
    name: ClassVar[str] = "Find Contours"
    description: ClassVar[str] = "Detect and draw object contours using Canny edges"
    category: ClassVar[str] = "edge"
    VERSION: ClassVar[int] = 2

    sigma: float = Field(default=1.0, ge=0.1, le=5.0,
                         json_schema_extra={"step": 0.1, "display_name": "Sigma"})
    low_threshold: float = Field(default=0.1, ge=0.01, le=0.5,
                                 json_schema_extra={"step": 0.01,
                                                    "display_name": "Low Threshold"})
    high_threshold: float = Field(default=0.2, ge=0.01, le=0.5,
                                  json_schema_extra={"step": 0.01,
                                                     "display_name": "High Threshold"})
    line_width: int = Field(default=2, ge=1, le=10,
                            json_schema_extra={"step": 1, "suffix": "px",
                                               "display_name": "Line Width"})
    color: str = Field(default="#000000",
                       json_schema_extra={"display_name": "Color"})

    def apply(self, image: np.ndarray) -> np.ndarray:
        edges = imagestag_rust.find_edges(image, float(self.sigma),
                                          float(self.low_threshold),
                                          float(self.high_threshold))

        if self.line_width > 1:
            edges = imagestag_rust.dilate(edges, float(self.line_width - 1))

        mask = edges[:, :, 0].astype(np.float32) / 255.0

        c = self.color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

        result = np.zeros_like(image)
        result[:, :, 0] = (mask * r).astype(np.uint8)
        result[:, :, 1] = (mask * g).astype(np.uint8)
        result[:, :, 2] = (mask * b).astype(np.uint8)
        result[:, :, 3] = (mask * 255).astype(np.uint8)
        return result
