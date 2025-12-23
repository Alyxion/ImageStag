# ImageStag - Sample Media
"""
Sample images and videos for ImageStag demos and testing.

All samples are public domain (CC0) or have appropriate licenses
for redistribution without attribution.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imagestag import Image

# Base path for sample media
SAMPLES_DIR = Path(__file__).parent


def _load_image(filename: str) -> 'Image':
    """Load an image from the samples directory."""
    from imagestag import Image
    path = SAMPLES_DIR / 'images' / filename
    if not path.exists():
        raise FileNotFoundError(f"Sample image not found: {filename}")
    return Image(str(path))


def group() -> 'Image':
    """Group of 5 people (800x533, RGB).

    Good for face detection demos with multiple faces.
    Source: Pexels (CC0/Public Domain)
    """
    return _load_image('group.jpg')


def stag() -> 'Image':
    """ImageStag logo/mascot image.

    The stag sample image included with ImageStag.
    """
    return _load_image('stag.jpg')


def list_images() -> list[str]:
    """List all available sample images.

    Returns:
        List of image names that can be loaded.
    """
    return ['group', 'stag']


def load(name: str) -> 'Image':
    """Load sample image by name.

    Args:
        name: Image name (see list_images())

    Returns:
        Image object

    Example:
        from imagestag.samples import load
        img = load('group')
    """
    images = {
        'group': group,
        'faces': group,  # Alias
        'stag': stag,
    }

    name = name.lower()
    if name not in images:
        available = ', '.join(sorted(images.keys()))
        raise ValueError(f"Unknown sample: {name}. Available: {available}")

    return images[name]()


__all__ = [
    'group',
    'stag',
    'list_images',
    'load',
    'SAMPLES_DIR',
]
