"""Noise and denoising filters."""

import numpy as np
import cv2

from .base import BaseFilter
from .registry import register_filter


@register_filter("add_noise")
class AddNoiseFilter(BaseFilter):
    """Add noise to image."""

    name = "Add Noise"
    description = "Add random noise to the image"
    category = "noise"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "noise_type",
                "name": "Noise Type",
                "type": "select",
                "options": ["gaussian", "salt_pepper", "poisson", "speckle"],
                "default": "gaussian",
            },
            {
                "id": "amount",
                "name": "Amount",
                "type": "range",
                "min": 0,
                "max": 100,
                "step": 1,
                "default": 20,
            },
        ]

    def apply(self, image: np.ndarray, noise_type: str = "gaussian", amount: int = 20) -> np.ndarray:
        result = image.copy().astype(np.float32)
        rgb = result[:, :, :3]

        if noise_type == "gaussian":
            # Gaussian noise
            sigma = amount * 2.55  # Scale to 0-255 range
            noise = np.random.normal(0, sigma, rgb.shape)
            rgb = rgb + noise

        elif noise_type == "salt_pepper":
            # Salt and pepper noise
            prob = amount / 200.0  # Scale probability
            # Salt (white)
            salt = np.random.random(rgb.shape[:2]) < prob
            rgb[salt] = 255
            # Pepper (black)
            pepper = np.random.random(rgb.shape[:2]) < prob
            rgb[pepper] = 0

        elif noise_type == "poisson":
            # Poisson noise
            vals = len(np.unique(rgb))
            vals = 2 ** np.ceil(np.log2(vals))
            noisy = np.random.poisson(rgb * vals / 255) / float(vals) * 255
            noise_strength = amount / 100.0
            rgb = rgb * (1 - noise_strength) + noisy * noise_strength

        elif noise_type == "speckle":
            # Speckle noise (multiplicative)
            sigma = amount / 100.0
            noise = np.random.randn(*rgb.shape) * sigma
            rgb = rgb + rgb * noise

        result[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        return result.astype(np.uint8)


@register_filter("denoise")
class DenoiseFilter(BaseFilter):
    """Remove noise using Non-local Means denoising."""

    name = "Denoise"
    description = "Remove noise using Non-local Means algorithm"
    category = "noise"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "strength",
                "name": "Strength",
                "type": "range",
                "min": 1,
                "max": 30,
                "step": 1,
                "default": 10,
            },
            {
                "id": "search_window",
                "name": "Search Window",
                "type": "range",
                "min": 7,
                "max": 31,
                "step": 2,
                "default": 21,
            },
            {
                "id": "block_size",
                "name": "Block Size",
                "type": "range",
                "min": 3,
                "max": 11,
                "step": 2,
                "default": 7,
            },
        ]

    def apply(self, image: np.ndarray, strength: int = 10, search_window: int = 21, block_size: int = 7) -> np.ndarray:
        rgb = image[:, :, :3]

        # OpenCV's fast NL means denoising for color images
        denoised = cv2.fastNlMeansDenoisingColored(rgb, None, strength, strength, block_size, search_window)

        result = np.concatenate([denoised, image[:, :, 3:4]], axis=2)
        return result


@register_filter("denoise_tv")
class DenoiseTVFilter(BaseFilter):
    """Total Variation denoising."""

    name = "Denoise (TV)"
    description = "Remove noise using Total Variation denoising"
    category = "noise"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "weight",
                "name": "Weight",
                "type": "range",
                "min": 0.01,
                "max": 0.5,
                "step": 0.01,
                "default": 0.1,
            },
        ]

    def apply(self, image: np.ndarray, weight: float = 0.1) -> np.ndarray:
        from skimage.restoration import denoise_tv_chambolle

        rgb = image[:, :, :3].astype(np.float32) / 255.0

        denoised = denoise_tv_chambolle(rgb, weight=weight, channel_axis=2)
        denoised = (denoised * 255).astype(np.uint8)

        result = np.concatenate([denoised, image[:, :, 3:4]], axis=2)
        return result


@register_filter("denoise_wavelet")
class DenoiseWaveletFilter(BaseFilter):
    """Wavelet denoising."""

    name = "Denoise (Wavelet)"
    description = "Remove noise using Wavelet denoising"
    category = "noise"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "sigma",
                "name": "Sigma",
                "type": "range",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.0,
            },
            {
                "id": "wavelet",
                "name": "Wavelet",
                "type": "select",
                "options": ["db1", "db2", "haar", "sym2", "coif1"],
                "default": "db1",
            },
        ]

    def apply(self, image: np.ndarray, sigma: float = 0.0, wavelet: str = "db1") -> np.ndarray:
        from skimage.restoration import denoise_wavelet

        rgb = image[:, :, :3].astype(np.float32) / 255.0

        # sigma=None means estimate from data
        sigma_val = sigma if sigma > 0 else None
        denoised = denoise_wavelet(rgb, sigma=sigma_val, wavelet=wavelet, channel_axis=2, rescale_sigma=True)
        denoised = (np.clip(denoised, 0, 1) * 255).astype(np.uint8)

        result = np.concatenate([denoised, image[:, :, 3:4]], axis=2)
        return result


@register_filter("denoise_bilateral")
class DenoiseBilateralFilter(BaseFilter):
    """Bilateral denoising (edge-preserving)."""

    name = "Denoise (Bilateral)"
    description = "Edge-preserving noise removal using bilateral filter"
    category = "noise"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "sigma_color",
                "name": "Color Sigma",
                "type": "range",
                "min": 0.01,
                "max": 0.5,
                "step": 0.01,
                "default": 0.1,
            },
            {
                "id": "sigma_spatial",
                "name": "Spatial Sigma",
                "type": "range",
                "min": 1,
                "max": 30,
                "step": 1,
                "default": 15,
            },
        ]

    def apply(self, image: np.ndarray, sigma_color: float = 0.1, sigma_spatial: int = 15) -> np.ndarray:
        from skimage.restoration import denoise_bilateral

        rgb = image[:, :, :3].astype(np.float32) / 255.0

        denoised = denoise_bilateral(rgb, sigma_color=sigma_color, sigma_spatial=sigma_spatial, channel_axis=2)
        denoised = (denoised * 255).astype(np.uint8)

        result = np.concatenate([denoised, image[:, :, 3:4]], axis=2)
        return result


@register_filter("remove_hot_pixels")
class RemoveHotPixelsFilter(BaseFilter):
    """Remove hot/dead pixels."""

    name = "Remove Hot Pixels"
    description = "Remove hot and dead pixels using median filter on outliers"
    category = "noise"
    version = 1

    @classmethod
    def get_params_schema(cls):
        return [
            {
                "id": "threshold",
                "name": "Threshold",
                "type": "range",
                "min": 10,
                "max": 100,
                "step": 5,
                "default": 50,
            },
        ]

    def apply(self, image: np.ndarray, threshold: int = 50) -> np.ndarray:
        from scipy import ndimage

        result = image.copy()

        for c in range(3):
            channel = image[:, :, c].astype(np.float32)
            # Get median filtered version
            median = ndimage.median_filter(channel, size=3)
            # Find outliers
            diff = np.abs(channel - median)
            outliers = diff > threshold
            # Replace outliers with median
            result[:, :, c][outliers] = median[outliers]

        return result
