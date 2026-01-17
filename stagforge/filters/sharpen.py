"""Sharpen filters."""

import numpy as np
from skimage.filters import unsharp_mask

from .base import BaseFilter
from .registry import register_filter


@register_filter("unsharp_mask")
class UnsharpMaskFilter(BaseFilter):
    """Unsharp mask sharpening filter."""

    name = "Unsharp Mask"
    description = "Sharpen image using unsharp masking"
    category = "sharpen"

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "radius",
                "name": "Radius",
                "type": "range",
                "min": 0.1,
                "max": 10.0,
                "step": 0.1,
                "default": 1.0,
            },
            {
                "id": "amount",
                "name": "Amount",
                "type": "range",
                "min": 0.1,
                "max": 5.0,
                "step": 0.1,
                "default": 1.0,
            },
        ]

    def apply(self, image: np.ndarray, radius: float = 1.0, amount: float = 1.0) -> np.ndarray:
        # Separate channels
        rgb = image[:, :, :3].astype(np.float32) / 255.0
        alpha = image[:, :, 3:4].astype(np.float32) / 255.0

        # Pre-multiply RGB by alpha to prevent edge artifacts
        rgb_premult = rgb * alpha

        # Apply unsharp mask to pre-multiplied RGB
        sharpened_premult = unsharp_mask(rgb_premult, radius=radius, amount=amount, channel_axis=2)

        # Un-premultiply (avoid division by zero)
        alpha_safe = np.maximum(alpha, 1e-6)
        rgb_result = sharpened_premult / alpha_safe
        rgb_result = np.clip(rgb_result, 0, 1)

        # Convert back to uint8
        rgb_uint8 = (rgb_result * 255).astype(np.uint8)
        alpha_uint8 = image[:, :, 3:4]  # Preserve original alpha for sharpen

        result = np.concatenate([rgb_uint8, alpha_uint8], axis=2)
        return result
