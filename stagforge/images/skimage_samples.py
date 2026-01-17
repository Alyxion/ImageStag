"""scikit-image sample images provider."""

from typing import Any

import numpy as np
from skimage import data

from .providers import BaseImageProvider, register_provider


@register_provider("skimage")
class SkimageSampleProvider(BaseImageProvider):
    """Provider for scikit-image sample images."""

    name = "scikit-image Samples"
    description = "Standard test images from scikit-image"

    # Map of image IDs to (loader_function, description)
    IMAGES = {
        "astronaut": (data.astronaut, "Astronaut - Color portrait (512x512)"),
        "camera": (data.camera, "Cameraman - Grayscale classic (512x512)"),
        "chelsea": (data.chelsea, "Chelsea the Cat - Color (300x451)"),
        "coffee": (data.coffee, "Coffee Cup - Color (400x600)"),
        "coins": (data.coins, "Coins - Grayscale (303x384)"),
        "horse": (data.horse, "Horse Silhouette - Binary (328x400)"),
        "hubble_deep_field": (data.hubble_deep_field, "Hubble Deep Field - Color (872x1000)"),
        "moon": (data.moon, "Moon Surface - Grayscale (512x512)"),
        "rocket": (data.rocket, "Rocket - Grayscale (427x640)"),
        "page": (data.page, "Page of Text - Grayscale (191x384)"),
        "grass": (data.grass, "Grass Texture - Grayscale (512x512)"),
        "gravel": (data.gravel, "Gravel Texture - Grayscale (512x512)"),
        "brick": (data.brick, "Brick Wall - Grayscale (512x512)"),
    }

    def list_images(self) -> list[dict[str, Any]]:
        """List available images."""
        return [{"id": img_id, "name": desc} for img_id, (_, desc) in self.IMAGES.items()]

    def get_image(self, image_id: str) -> tuple[np.ndarray, dict[str, Any]]:
        """Get image data and metadata."""
        if image_id not in self.IMAGES:
            raise KeyError(f"Unknown image: {image_id}")

        loader, description = self.IMAGES[image_id]
        image = loader()

        # Ensure uint8
        if image.dtype != np.uint8:
            if image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
            else:
                image = image.astype(np.uint8)

        metadata = {"name": image_id, "description": description, "source": "skimage"}

        return image, metadata
