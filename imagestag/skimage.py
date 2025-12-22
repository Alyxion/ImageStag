# ImageStag - scikit-image Sample Images
"""
Access to scikit-image sample images.

Provides convenient access to sample images from scikit-image for testing
and demonstration purposes.

Requires: pip install imagestag[skimage]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imagestag import Image


class SKImage:
    """Access to scikit-image sample images.

    Provides sample images from scikit-image as ImageStag Image objects.

    Example:
        from imagestag.skimage import SKImage

        # Get astronaut image
        img = SKImage.astronaut()

        # Get grayscale camera image
        img = SKImage.camera()

        # List all available images
        print(SKImage.list_images())
    """

    @staticmethod
    def _to_image(array, name: str = 'sample') -> 'Image':
        """Convert numpy array to Image."""
        from imagestag import Image
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Handle grayscale images
        if array.ndim == 2:
            # Convert to RGB
            array = np.stack([array, array, array], axis=-1)
            pf = PixelFormat.RGB
        elif array.ndim == 3:
            if array.shape[2] == 4:
                pf = PixelFormat.RGBA
            else:
                pf = PixelFormat.RGB
        else:
            raise ValueError(f"Unexpected array shape: {array.shape}")

        # Ensure uint8
        if array.dtype != np.uint8:
            if array.max() <= 1.0:
                array = (array * 255).astype(np.uint8)
            else:
                array = array.astype(np.uint8)

        return Image(array, pixel_format=pf)

    @classmethod
    def astronaut(cls) -> 'Image':
        """Astronaut Eileen Collins (512x512, RGB).

        Color image of NASA astronaut Eileen Collins.
        """
        from skimage import data
        return cls._to_image(data.astronaut(), 'astronaut')

    @classmethod
    def camera(cls) -> 'Image':
        """Cameraman (512x512, grayscale).

        Classic grayscale test image.
        """
        from skimage import data
        return cls._to_image(data.camera(), 'camera')

    @classmethod
    def chelsea(cls) -> 'Image':
        """Chelsea the cat (300x451, RGB).

        Color image of a tabby cat.
        """
        from skimage import data
        return cls._to_image(data.chelsea(), 'chelsea')

    @classmethod
    def coffee(cls) -> 'Image':
        """Coffee cup (400x600, RGB).

        Color image of a coffee cup.
        """
        from skimage import data
        return cls._to_image(data.coffee(), 'coffee')

    @classmethod
    def coins(cls) -> 'Image':
        """Greek coins (303x384, grayscale).

        Grayscale image of coins, good for segmentation demos.
        """
        from skimage import data
        return cls._to_image(data.coins(), 'coins')

    @classmethod
    def horse(cls) -> 'Image':
        """Horse silhouette (328x400, binary).

        Binary image of a horse, good for morphology demos.
        """
        from skimage import data
        import numpy as np
        # Convert binary to uint8
        horse = data.horse().astype(np.uint8) * 255
        return cls._to_image(horse, 'horse')

    @classmethod
    def hubble_deep_field(cls) -> 'Image':
        """Hubble deep field (872x1000, RGB).

        Hubble Space Telescope deep field image.
        """
        from skimage import data
        return cls._to_image(data.hubble_deep_field(), 'hubble')

    @classmethod
    def immunohistochemistry(cls) -> 'Image':
        """Immunohistochemistry (512x512, RGB).

        Color image of stained tissue.
        """
        from skimage import data
        return cls._to_image(data.immunohistochemistry(), 'ihc')

    @classmethod
    def moon(cls) -> 'Image':
        """Moon surface (512x512, grayscale).

        Grayscale image of lunar surface.
        """
        from skimage import data
        return cls._to_image(data.moon(), 'moon')

    @classmethod
    def page(cls) -> 'Image':
        """Scanned text page (191x384, grayscale).

        Grayscale image of printed text, good for OCR demos.
        """
        from skimage import data
        return cls._to_image(data.page(), 'page')

    @classmethod
    def rocket(cls) -> 'Image':
        """Rocket (427x640, RGB).

        Color image of a rocket launch.
        """
        from skimage import data
        return cls._to_image(data.rocket(), 'rocket')

    @classmethod
    def text(cls) -> 'Image':
        """Text sample (172x448, grayscale).

        Grayscale image of text.
        """
        from skimage import data
        return cls._to_image(data.text(), 'text')

    @classmethod
    def cat(cls) -> 'Image':
        """Alias for chelsea() - cat image."""
        return cls.chelsea()

    @classmethod
    def face(cls) -> 'Image':
        """Alias for astronaut() - face image for face detection demos."""
        return cls.astronaut()

    @classmethod
    def list_images(cls) -> list[str]:
        """List all available sample images.

        Returns:
            List of image names that can be loaded.
        """
        return [
            'astronaut',
            'camera',
            'chelsea',
            'coffee',
            'coins',
            'horse',
            'hubble_deep_field',
            'immunohistochemistry',
            'moon',
            'page',
            'rocket',
            'text',
        ]

    @classmethod
    def load(cls, name: str) -> 'Image':
        """Load sample image by name.

        Args:
            name: Image name (see list_images())

        Returns:
            Image object

        Example:
            img = SKImage.load('astronaut')
        """
        images = {
            'astronaut': cls.astronaut,
            'camera': cls.camera,
            'chelsea': cls.chelsea,
            'cat': cls.chelsea,
            'coffee': cls.coffee,
            'coins': cls.coins,
            'horse': cls.horse,
            'hubble_deep_field': cls.hubble_deep_field,
            'hubble': cls.hubble_deep_field,
            'immunohistochemistry': cls.immunohistochemistry,
            'ihc': cls.immunohistochemistry,
            'moon': cls.moon,
            'page': cls.page,
            'rocket': cls.rocket,
            'text': cls.text,
            'face': cls.astronaut,
        }

        name = name.lower()
        if name not in images:
            available = ', '.join(sorted(images.keys()))
            raise ValueError(f"Unknown image: {name}. Available: {available}")

        return images[name]()
