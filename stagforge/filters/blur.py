"""Blur filters."""

import numpy as np
from scipy import ndimage
from skimage.filters import gaussian

from .base import BaseFilter
from .registry import register_filter


def apply_blur_alpha_aware(image: np.ndarray, blur_func, **kwargs) -> np.ndarray:
    """
    Apply blur filter with proper alpha handling.
    Uses pre-multiplied alpha to prevent black edges on transparent areas.

    Args:
        image: RGBA image as uint8 array
        blur_func: Function that takes a float32 array and returns blurred result
        **kwargs: Additional arguments passed to blur_func

    Returns:
        Blurred RGBA image as uint8 array
    """
    # Separate channels and convert to float
    rgb = image[:, :, :3].astype(np.float32) / 255.0
    alpha = image[:, :, 3:4].astype(np.float32) / 255.0

    # Pre-multiply RGB by alpha
    rgb_premult = rgb * alpha

    # Apply blur to pre-multiplied RGB and alpha separately
    rgb_blurred = blur_func(rgb_premult, **kwargs)
    alpha_blurred = blur_func(alpha, **kwargs)

    # Un-premultiply (avoid division by zero)
    alpha_safe = np.maximum(alpha_blurred, 1e-6)
    rgb_result = rgb_blurred / alpha_safe
    rgb_result = np.clip(rgb_result, 0, 1)

    # Convert back to uint8
    rgb_uint8 = (rgb_result * 255).astype(np.uint8)
    alpha_uint8 = (np.clip(alpha_blurred, 0, 1) * 255).astype(np.uint8)

    # Recombine
    result = np.concatenate([rgb_uint8, alpha_uint8], axis=2)
    return result


@register_filter("gaussian_blur")
class GaussianBlurFilter(BaseFilter):
    """Gaussian blur filter."""

    name = "Gaussian Blur"
    description = "Apply Gaussian blur to soften the image"
    category = "blur"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "sigma",
                "name": "Blur Radius",
                "type": "range",
                "min": 0.1,
                "max": 20.0,
                "step": 0.1,
                "default": 3.0,
            }
        ]

    def apply(self, image: np.ndarray, sigma: float = 3.0) -> np.ndarray:
        def gaussian_blur(arr, sigma):
            # Handle both RGB (H,W,3) and alpha (H,W,1) arrays
            if arr.ndim == 3 and arr.shape[2] > 1:
                return gaussian(arr, sigma=sigma, channel_axis=2)
            else:
                # For single channel, squeeze and unsqueeze
                squeezed = arr.squeeze()
                blurred = gaussian(squeezed, sigma=sigma)
                return blurred[:, :, np.newaxis]

        return apply_blur_alpha_aware(image, gaussian_blur, sigma=sigma)


@register_filter("box_blur")
class BoxBlurFilter(BaseFilter):
    """Box (uniform) blur filter."""

    name = "Box Blur"
    description = "Apply uniform box blur"
    category = "blur"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "size",
                "name": "Kernel Size",
                "type": "range",
                "min": 1,
                "max": 50,
                "step": 1,
                "default": 5,
            }
        ]

    def apply(self, image: np.ndarray, size: int = 5) -> np.ndarray:
        def box_blur(arr, size):
            if arr.ndim == 3:
                result = np.zeros_like(arr)
                for c in range(arr.shape[2]):
                    result[:, :, c] = ndimage.uniform_filter(arr[:, :, c], size=size, mode='constant', cval=0)
                return result
            else:
                return ndimage.uniform_filter(arr, size=size, mode='constant', cval=0)

        return apply_blur_alpha_aware(image, box_blur, size=size)


@register_filter("median_blur")
class MedianBlurFilter(BaseFilter):
    """Median blur filter - good for noise reduction."""

    name = "Median Blur"
    description = "Apply median filter to reduce noise while preserving edges"
    category = "blur"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "size",
                "name": "Kernel Size",
                "type": "range",
                "min": 1,
                "max": 21,
                "step": 2,
                "default": 3,
            }
        ]

    def apply(self, image: np.ndarray, size: int = 3) -> np.ndarray:
        # Ensure odd kernel size
        size = size if size % 2 == 1 else size + 1

        def median_blur(arr, size):
            if arr.ndim == 3:
                result = np.zeros_like(arr)
                for c in range(arr.shape[2]):
                    result[:, :, c] = ndimage.median_filter(arr[:, :, c], size=size, mode='constant', cval=0)
                return result
            else:
                return ndimage.median_filter(arr, size=size, mode='constant', cval=0)

        return apply_blur_alpha_aware(image, median_blur, size=size)


@register_filter("bilateral_blur")
class BilateralBlurFilter(BaseFilter):
    """Bilateral filter - edge-preserving smoothing."""

    name = "Bilateral Filter"
    description = "Edge-preserving smoothing that reduces noise while keeping edges sharp"
    category = "blur"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "sigma_color",
                "name": "Color Sigma",
                "type": "range",
                "min": 1,
                "max": 150,
                "step": 1,
                "default": 75,
            },
            {
                "id": "sigma_spatial",
                "name": "Spatial Sigma",
                "type": "range",
                "min": 1,
                "max": 50,
                "step": 1,
                "default": 10,
            },
        ]

    def apply(self, image: np.ndarray, sigma_color: int = 75, sigma_spatial: int = 10) -> np.ndarray:
        import cv2

        # Separate channels
        rgb = image[:, :, :3].astype(np.float32) / 255.0
        alpha = image[:, :, 3:4].astype(np.float32) / 255.0

        # Pre-multiply RGB by alpha
        rgb_premult = (rgb * alpha * 255).astype(np.uint8)

        # Apply bilateral filter to pre-multiplied RGB
        filtered_premult = cv2.bilateralFilter(rgb_premult, d=-1, sigmaColor=sigma_color, sigmaSpace=sigma_spatial)

        # Also blur alpha for consistency
        alpha_uint8 = (alpha * 255).astype(np.uint8)
        alpha_blurred = cv2.bilateralFilter(alpha_uint8, d=-1, sigmaColor=sigma_color, sigmaSpace=sigma_spatial)

        # Un-premultiply
        filtered_float = filtered_premult.astype(np.float32) / 255.0
        alpha_float = alpha_blurred.astype(np.float32) / 255.0
        alpha_safe = np.maximum(alpha_float, 1e-6)
        rgb_result = filtered_float / alpha_safe[:, :, np.newaxis]
        rgb_result = np.clip(rgb_result, 0, 1)

        # Convert back to uint8
        rgb_uint8 = (rgb_result * 255).astype(np.uint8)

        result = np.concatenate([rgb_uint8, alpha_blurred], axis=2)
        return result


@register_filter("motion_blur")
class MotionBlurFilter(BaseFilter):
    """Motion blur filter."""

    name = "Motion Blur"
    description = "Apply directional motion blur effect"
    category = "blur"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "size",
                "name": "Blur Length",
                "type": "range",
                "min": 3,
                "max": 50,
                "step": 1,
                "default": 15,
            },
            {
                "id": "angle",
                "name": "Angle",
                "type": "range",
                "min": 0,
                "max": 360,
                "step": 1,
                "default": 0,
            },
        ]

    def apply(self, image: np.ndarray, size: int = 15, angle: int = 0) -> np.ndarray:
        import cv2

        # Create motion blur kernel
        kernel = np.zeros((size, size))
        kernel[size // 2, :] = np.ones(size)
        kernel = kernel / size

        # Rotate kernel by angle
        center = (size / 2, size / 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        kernel = cv2.warpAffine(kernel, rotation_matrix, (size, size))
        kernel = kernel / kernel.sum()  # Normalize

        # Separate channels
        rgb = image[:, :, :3].astype(np.float32) / 255.0
        alpha = image[:, :, 3:4].astype(np.float32) / 255.0

        # Pre-multiply RGB by alpha
        rgb_premult = (rgb * alpha * 255).astype(np.uint8)

        # Apply motion blur to pre-multiplied RGB
        filtered_premult = cv2.filter2D(rgb_premult, -1, kernel)

        # Also blur alpha
        alpha_uint8 = (alpha * 255).astype(np.uint8)
        alpha_blurred = cv2.filter2D(alpha_uint8, -1, kernel)

        # Un-premultiply
        filtered_float = filtered_premult.astype(np.float32) / 255.0
        alpha_float = alpha_blurred.astype(np.float32) / 255.0
        alpha_safe = np.maximum(alpha_float, 1e-6)
        rgb_result = filtered_float / alpha_safe
        rgb_result = np.clip(rgb_result, 0, 1)

        # Convert back to uint8
        rgb_uint8 = (rgb_result * 255).astype(np.uint8)

        result = np.concatenate([rgb_uint8, alpha_blurred], axis=2)
        return result
