"""Image provider base and registry."""

from abc import ABC, abstractmethod
from typing import Any, Type

import numpy as np


class BaseImageProvider(ABC):
    """Base class for image providers."""

    name: str = "Base Provider"
    description: str = ""

    @abstractmethod
    def list_images(self) -> list[dict[str, Any]]:
        """List available images."""
        pass

    @abstractmethod
    def get_image(self, image_id: str) -> tuple[np.ndarray, dict[str, Any]]:
        """Get image data and metadata."""
        pass


# Global provider registry
image_providers: dict[str, BaseImageProvider] = {}


def register_provider(provider_id: str):
    """Decorator to register an image provider."""

    def decorator(cls: Type[BaseImageProvider]):
        image_providers[provider_id] = cls()
        return cls

    return decorator


def load_providers():
    """Load all built-in providers."""
    from . import skimage_samples  # noqa: F401
