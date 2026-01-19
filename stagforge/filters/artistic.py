"""Artistic effect filters."""

import numpy as np
import cv2

from .base import BaseFilter
from .registry import register_filter


@register_filter("emboss")
class EmbossFilter(BaseFilter):
    """Emboss effect filter."""

    name = "Emboss"
    description = "Create an embossed 3D effect"
    category = "artistic"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "strength",
                "name": "Strength",
                "type": "range",
                "min": 0.5,
                "max": 3.0,
                "step": 0.1,
                "default": 1.0,
            },
            {
                "id": "direction",
                "name": "Direction",
                "type": "select",
                "options": ["top_left", "top", "top_right", "left", "right", "bottom_left", "bottom", "bottom_right"],
                "default": "top_left",
            },
        ]

    def apply(self, image: np.ndarray, strength: float = 1.0, direction: str = "top_left") -> np.ndarray:
        # Emboss kernels for different directions
        kernels = {
            "top_left": np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]]),
            "top": np.array([[-1, -2, -1], [0, 1, 0], [1, 2, 1]]),
            "top_right": np.array([[0, -1, -2], [1, 1, -1], [2, 1, 0]]),
            "left": np.array([[-1, 0, 1], [-2, 1, 2], [-1, 0, 1]]),
            "right": np.array([[1, 0, -1], [2, 1, -2], [1, 0, -1]]),
            "bottom_left": np.array([[0, 1, 2], [-1, 1, 1], [-2, -1, 0]]),
            "bottom": np.array([[1, 2, 1], [0, 1, 0], [-1, -2, -1]]),
            "bottom_right": np.array([[2, 1, 0], [1, 1, -1], [0, -1, -2]]),
        }

        kernel = kernels.get(direction, kernels["top_left"]) * strength

        rgb = image[:, :, :3].astype(np.float32)
        embossed = cv2.filter2D(rgb, -1, kernel)
        embossed = embossed + 128  # Shift to mid-gray
        embossed = np.clip(embossed, 0, 255).astype(np.uint8)

        result = np.concatenate([embossed, image[:, :, 3:4]], axis=2)
        return result


@register_filter("oil_painting")
class OilPaintingFilter(BaseFilter):
    """Oil painting effect."""

    name = "Oil Painting"
    description = "Apply an oil painting artistic effect"
    category = "artistic"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "size",
                "name": "Brush Size",
                "type": "range",
                "min": 1,
                "max": 10,
                "step": 1,
                "default": 4,
            },
            {
                "id": "dynratio",
                "name": "Dynamic Ratio",
                "type": "range",
                "min": 1,
                "max": 5,
                "step": 1,
                "default": 1,
            },
        ]

    def apply(self, image: np.ndarray, size: int = 4, dynratio: int = 1) -> np.ndarray:
        rgb = image[:, :, :3]

        # OpenCV's xphoto module has oil painting effect
        try:
            result_rgb = cv2.xphoto.oilPainting(rgb, size, dynratio)
        except AttributeError:
            # Fallback: simple bilateral filter approximation
            result_rgb = cv2.bilateralFilter(rgb, size * 2, 75, 75)
            result_rgb = cv2.bilateralFilter(result_rgb, size * 2, 75, 75)

        result = np.concatenate([result_rgb, image[:, :, 3:4]], axis=2)
        return result


@register_filter("pencil_sketch")
class PencilSketchFilter(BaseFilter):
    """Pencil sketch effect."""

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
                "min": 0.01,
                "max": 0.2,
                "step": 0.01,
                "default": 0.07,
            },
            {
                "id": "shade_factor",
                "name": "Shade Factor",
                "type": "range",
                "min": 0.0,
                "max": 0.1,
                "step": 0.01,
                "default": 0.05,
            },
        ]

    def apply(self, image: np.ndarray, sigma_s: int = 60, sigma_r: float = 0.07, shade_factor: float = 0.05) -> np.ndarray:
        rgb = image[:, :, :3]

        # Create pencil sketch
        gray_sketch, color_sketch = cv2.pencilSketch(rgb, sigma_s=sigma_s, sigma_r=sigma_r, shade_factor=shade_factor)

        # Use grayscale sketch
        result = np.stack([gray_sketch, gray_sketch, gray_sketch, image[:, :, 3]], axis=2)
        return result


@register_filter("cartoon")
class CartoonFilter(BaseFilter):
    """Cartoon effect filter."""

    name = "Cartoon"
    description = "Apply cartoon-style effect"
    category = "artistic"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "num_downsamples",
                "name": "Smoothness",
                "type": "range",
                "min": 1,
                "max": 4,
                "step": 1,
                "default": 2,
            },
            {
                "id": "num_bilateral",
                "name": "Bilateral Iterations",
                "type": "range",
                "min": 1,
                "max": 10,
                "step": 1,
                "default": 5,
            },
        ]

    def apply(self, image: np.ndarray, num_downsamples: int = 2, num_bilateral: int = 5) -> np.ndarray:
        rgb = image[:, :, :3]

        # Downsample
        img_color = rgb.copy()
        for _ in range(num_downsamples):
            img_color = cv2.pyrDown(img_color)

        # Apply bilateral filter
        for _ in range(num_bilateral):
            img_color = cv2.bilateralFilter(img_color, 9, 9, 7)

        # Upsample
        for _ in range(num_downsamples):
            img_color = cv2.pyrUp(img_color)

        # Resize to match original
        img_color = cv2.resize(img_color, (rgb.shape[1], rgb.shape[0]))

        # Convert to gray and detect edges
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        gray = cv2.medianBlur(gray, 7)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2)

        # Combine color and edges
        edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        cartoon = cv2.bitwise_and(img_color, edges_colored)

        result = np.concatenate([cartoon, image[:, :, 3:4]], axis=2)
        return result


@register_filter("stylization")
class StylizationFilter(BaseFilter):
    """Edge-preserving stylization."""

    name = "Stylization"
    description = "Apply artistic stylization effect"
    category = "artistic"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "sigma_s",
                "name": "Sigma Spatial",
                "type": "range",
                "min": 10,
                "max": 200,
                "step": 10,
                "default": 60,
            },
            {
                "id": "sigma_r",
                "name": "Sigma Range",
                "type": "range",
                "min": 0.1,
                "max": 1.0,
                "step": 0.1,
                "default": 0.45,
            },
        ]

    def apply(self, image: np.ndarray, sigma_s: int = 60, sigma_r: float = 0.45) -> np.ndarray:
        rgb = image[:, :, :3]

        stylized = cv2.stylization(rgb, sigma_s=sigma_s, sigma_r=sigma_r)

        result = np.concatenate([stylized, image[:, :, 3:4]], axis=2)
        return result


@register_filter("detail_enhance")
class DetailEnhanceFilter(BaseFilter):
    """Enhance fine details."""

    name = "Detail Enhance"
    description = "Enhance fine image details"
    category = "artistic"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "sigma_s",
                "name": "Sigma Spatial",
                "type": "range",
                "min": 10,
                "max": 200,
                "step": 10,
                "default": 10,
            },
            {
                "id": "sigma_r",
                "name": "Sigma Range",
                "type": "range",
                "min": 0.01,
                "max": 1.0,
                "step": 0.01,
                "default": 0.15,
            },
        ]

    def apply(self, image: np.ndarray, sigma_s: int = 10, sigma_r: float = 0.15) -> np.ndarray:
        rgb = image[:, :, :3]

        enhanced = cv2.detailEnhance(rgb, sigma_s=sigma_s, sigma_r=sigma_r)

        result = np.concatenate([enhanced, image[:, :, 3:4]], axis=2)
        return result


@register_filter("edge_preserving")
class EdgePreservingFilter(BaseFilter):
    """Edge-preserving smoothing."""

    name = "Edge Preserving Smooth"
    description = "Smooth image while preserving edges"
    category = "artistic"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "sigma_s",
                "name": "Sigma Spatial",
                "type": "range",
                "min": 10,
                "max": 200,
                "step": 10,
                "default": 60,
            },
            {
                "id": "sigma_r",
                "name": "Sigma Range",
                "type": "range",
                "min": 0.1,
                "max": 1.0,
                "step": 0.1,
                "default": 0.4,
            },
        ]

    def apply(self, image: np.ndarray, sigma_s: int = 60, sigma_r: float = 0.4) -> np.ndarray:
        rgb = image[:, :, :3]

        smoothed = cv2.edgePreservingFilter(rgb, flags=1, sigma_s=sigma_s, sigma_r=sigma_r)

        result = np.concatenate([smoothed, image[:, :, 3:4]], axis=2)
        return result


@register_filter("pixelate")
class PixelateFilter(BaseFilter):
    """Pixelation effect."""

    name = "Pixelate"
    description = "Apply pixelation/mosaic effect"
    category = "artistic"
    version = 1

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
            },
        ]

    def apply(self, image: np.ndarray, block_size: int = 10) -> np.ndarray:
        h, w = image.shape[:2]
        rgb = image[:, :, :3]

        # Downsample then upsample with nearest neighbor
        small = cv2.resize(rgb, (w // block_size, h // block_size), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

        result = np.concatenate([pixelated, image[:, :, 3:4]], axis=2)
        return result


@register_filter("vignette")
class VignetteFilter(BaseFilter):
    """Vignette effect (darkened corners)."""

    name = "Vignette"
    description = "Add darkened corners vignette effect"
    category = "artistic"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "strength",
                "name": "Strength",
                "type": "range",
                "min": 0.1,
                "max": 2.0,
                "step": 0.1,
                "default": 0.8,
            },
            {
                "id": "radius",
                "name": "Radius",
                "type": "range",
                "min": 0.1,
                "max": 2.0,
                "step": 0.1,
                "default": 1.0,
            },
        ]

    def apply(self, image: np.ndarray, strength: float = 0.8, radius: float = 1.0) -> np.ndarray:
        h, w = image.shape[:2]
        rgb = image[:, :, :3].astype(np.float32)

        # Create vignette mask
        x = np.linspace(-1, 1, w)
        y = np.linspace(-1, 1, h)
        X, Y = np.meshgrid(x, y)
        dist = np.sqrt(X**2 + Y**2)

        # Create smooth falloff
        vignette = 1 - np.clip((dist - radius) * strength, 0, 1)
        vignette = vignette[:, :, np.newaxis]

        # Apply vignette
        result_rgb = (rgb * vignette).astype(np.uint8)

        result = np.concatenate([result_rgb, image[:, :, 3:4]], axis=2)
        return result
