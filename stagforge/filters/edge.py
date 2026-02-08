"""Edge detection filters."""

import numpy as np
import imagestag_rust

from .base import BaseFilter
from .registry import register_filter


@register_filter("edge_detect")
class EdgeDetectFilter(BaseFilter):
    """Combined edge detection with method selection."""

    name = "Edge Detection"
    description = "Detect edges using various methods"
    category = "edge"
    version = 2

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "method",
                "name": "Method",
                "type": "select",
                "options": ["sobel", "laplacian"],
                "default": "sobel",
            },
            {
                "id": "direction",
                "name": "Direction",
                "type": "select",
                "options": ["both", "horizontal", "vertical"],
                "default": "both",
                "visible_when": {"method": ["sobel"]},
            },
            {
                "id": "kernel_size",
                "name": "Kernel Size",
                "type": "select",
                "options": ["3", "5", "7"],
                "default": "3",
            },
        ]

    def apply(
        self,
        image: np.ndarray,
        method: str = "sobel",
        direction: str = "both",
        kernel_size: str = "3",
    ) -> np.ndarray:
        if method == "laplacian":
            return imagestag_rust.laplacian(image, int(kernel_size))
        else:
            direction_map = {"both": "both", "horizontal": "h", "vertical": "v"}
            return imagestag_rust.sobel(
                image, direction_map.get(direction, "both"), int(kernel_size)
            )


@register_filter("find_contours")
class FindContoursFilter(BaseFilter):
    """Find and draw contours using Canny edge detection."""

    name = "Find Contours"
    description = "Detect and draw object contours using Canny edges"
    category = "edge"
    version = 2

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "sigma",
                "name": "Sigma",
                "type": "range",
                "min": 0.1,
                "max": 5.0,
                "step": 0.1,
                "default": 1.0,
            },
            {
                "id": "low_threshold",
                "name": "Low Threshold",
                "type": "range",
                "min": 0.01,
                "max": 0.5,
                "step": 0.01,
                "default": 0.1,
            },
            {
                "id": "high_threshold",
                "name": "High Threshold",
                "type": "range",
                "min": 0.01,
                "max": 0.5,
                "step": 0.01,
                "default": 0.2,
            },
            {
                "id": "line_width",
                "name": "Line Width",
                "type": "range",
                "min": 1,
                "max": 10,
                "step": 1,
                "default": 2,
                "suffix": "px",
            },
            {
                "id": "color",
                "name": "Color",
                "type": "color",
                "default": "#000000",
            },
        ]

    def apply(self, image: np.ndarray, sigma: float = 1.0,
              low_threshold: float = 0.1, high_threshold: float = 0.2,
              line_width: int = 2, color: str = "#000000") -> np.ndarray:
        # Run Canny edge detection
        edges = imagestag_rust.find_edges(image, float(sigma), float(low_threshold), float(high_threshold))

        # Thicken edges if line_width > 1
        if line_width > 1:
            edges = imagestag_rust.dilate(edges, float(line_width - 1))

        # Build edge mask from luminance of Canny output
        mask = edges[:, :, 0].astype(np.float32) / 255.0

        # Parse color
        c = color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

        # Composite: edge pixels get the chosen color, rest stays black
        result = np.zeros_like(image)
        result[:, :, 0] = (mask * r).astype(np.uint8)
        result[:, :, 1] = (mask * g).astype(np.uint8)
        result[:, :, 2] = (mask * b).astype(np.uint8)
        result[:, :, 3] = (mask * 255).astype(np.uint8)
        return result
