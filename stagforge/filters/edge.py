"""Edge detection filters."""

import numpy as np
from skimage import filters
from skimage.feature import canny

from .base import BaseFilter
from .registry import register_filter


@register_filter("sobel_edge")
class SobelEdgeFilter(BaseFilter):
    """Sobel edge detection filter."""

    name = "Sobel Edge Detection"
    description = "Detect edges using Sobel operator"
    category = "edge"

    @classmethod
    def get_params_schema(cls):
        return []

    def apply(self, image: np.ndarray) -> np.ndarray:
        # Convert to grayscale for edge detection
        gray = np.mean(image[:, :, :3], axis=2).astype(np.float32) / 255.0

        edges = filters.sobel(gray)
        edges = (np.clip(edges, 0, 1) * 255).astype(np.uint8)

        # Convert back to RGBA
        result = np.stack([edges, edges, edges, image[:, :, 3]], axis=2)
        return result


@register_filter("canny_edge")
class CannyEdgeFilter(BaseFilter):
    """Canny edge detection filter."""

    name = "Canny Edge Detection"
    description = "Detect edges using Canny algorithm"
    category = "edge"

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
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "default": 0.1,
            },
            {
                "id": "high_threshold",
                "name": "High Threshold",
                "type": "range",
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "default": 0.2,
            },
        ]

    def apply(
        self,
        image: np.ndarray,
        sigma: float = 1.0,
        low_threshold: float = 0.1,
        high_threshold: float = 0.2,
    ) -> np.ndarray:
        gray = np.mean(image[:, :, :3], axis=2).astype(np.float32) / 255.0
        edges = canny(gray, sigma=sigma, low_threshold=low_threshold, high_threshold=high_threshold)
        edges = (edges * 255).astype(np.uint8)

        result = np.stack([edges, edges, edges, image[:, :, 3]], axis=2)
        return result


@register_filter("laplacian_edge")
class LaplacianEdgeFilter(BaseFilter):
    """Laplacian edge detection filter."""

    name = "Laplacian Edge Detection"
    description = "Detect edges using Laplacian operator"
    category = "edge"

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "ksize",
                "name": "Kernel Size",
                "type": "select",
                "options": ["1", "3", "5", "7"],
                "default": "3",
            }
        ]

    def apply(self, image: np.ndarray, ksize: str = "3") -> np.ndarray:
        import cv2

        gray = np.mean(image[:, :, :3], axis=2).astype(np.uint8)

        # Apply Laplacian
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=int(ksize))
        edges = np.abs(laplacian)
        edges = (np.clip(edges / edges.max() * 255, 0, 255) if edges.max() > 0 else edges).astype(np.uint8)

        result = np.stack([edges, edges, edges, image[:, :, 3]], axis=2)
        return result


@register_filter("prewitt_edge")
class PrewittEdgeFilter(BaseFilter):
    """Prewitt edge detection filter."""

    name = "Prewitt Edge Detection"
    description = "Detect edges using Prewitt operator"
    category = "edge"

    @classmethod
    def get_params_schema(cls):
        return []

    def apply(self, image: np.ndarray) -> np.ndarray:
        from skimage.filters import prewitt

        gray = np.mean(image[:, :, :3], axis=2).astype(np.float32) / 255.0
        edges = prewitt(gray)
        edges = (np.clip(edges, 0, 1) * 255).astype(np.uint8)

        result = np.stack([edges, edges, edges, image[:, :, 3]], axis=2)
        return result


@register_filter("scharr_edge")
class ScharrEdgeFilter(BaseFilter):
    """Scharr edge detection filter."""

    name = "Scharr Edge Detection"
    description = "Detect edges using Scharr operator (more accurate than Sobel)"
    category = "edge"

    @classmethod
    def get_params_schema(cls):
        return []

    def apply(self, image: np.ndarray) -> np.ndarray:
        from skimage.filters import scharr

        gray = np.mean(image[:, :, :3], axis=2).astype(np.float32) / 255.0
        edges = scharr(gray)
        edges = (np.clip(edges, 0, 1) * 255).astype(np.uint8)

        result = np.stack([edges, edges, edges, image[:, :, 3]], axis=2)
        return result


@register_filter("find_contours")
class FindContoursFilter(BaseFilter):
    """Find and draw contours."""

    name = "Find Contours"
    description = "Detect and draw object contours"
    category = "edge"

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
                "id": "line_width",
                "name": "Line Width",
                "type": "range",
                "min": 1,
                "max": 10,
                "step": 1,
                "default": 2,
            },
        ]

    def apply(self, image: np.ndarray, threshold: int = 128, line_width: int = 2) -> np.ndarray:
        import cv2

        gray = np.mean(image[:, :, :3], axis=2).astype(np.uint8)

        # Threshold
        _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Draw contours on result
        result = image.copy()
        cv2.drawContours(result[:, :, :3], contours, -1, (0, 255, 0), line_width)

        return result
