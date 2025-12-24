# ImageStag - ImageList
"""
ImageList class for handling lists of images with metadata.

Used by region processing pipelines where multiple image regions
flow through filters together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from imagestag import Image
    from imagestag.geometry_list import Geometry


@dataclass
class RegionMeta:
    """Metadata for a region extracted from an image.

    Stores information about where the region came from so it can
    be merged back into the original image.
    """

    # Original bounding box in source image (x, y, width, height)
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    # Padding applied during extraction
    padding: int = 0

    # Optional reference to original geometry
    geometry: 'Geometry | None' = None

    # Optional label/index
    label: str = ''
    index: int = 0

    # Extra user data
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def x2(self) -> int:
        """Right edge coordinate."""
        return self.x + self.width

    @property
    def y2(self) -> int:
        """Bottom edge coordinate."""
        return self.y + self.height

    def to_tuple(self) -> tuple[int, int, int, int]:
        """Return (x, y, width, height) tuple."""
        return (self.x, self.y, self.width, self.height)

    def to_bbox(self) -> tuple[int, int, int, int]:
        """Return (x1, y1, x2, y2) bounding box tuple."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class ImageList:
    """A list of images with metadata, typically from region extraction.

    Flows through filter pipelines as a unit. Regular filters automatically
    apply to each image in the list, preserving metadata.

    :ivar images: List of Image objects
    :ivar metadata: List of RegionMeta, one per image
    :ivar source_width: Width of the source image (for merging)
    :ivar source_height: Height of the source image (for merging)
    """

    images: list['Image'] = field(default_factory=list)
    metadata: list[RegionMeta] = field(default_factory=list)
    source_width: int = 0
    source_height: int = 0

    def __len__(self) -> int:
        return len(self.images)

    def __bool__(self) -> bool:
        return len(self.images) > 0

    def __iter__(self) -> Iterator['Image']:
        return iter(self.images)

    def __getitem__(self, index: int) -> 'Image':
        return self.images[index]

    def get_meta(self, index: int) -> RegionMeta:
        """Get metadata for image at index."""
        if index < len(self.metadata):
            return self.metadata[index]
        return RegionMeta()

    def add(self, image: 'Image', meta: RegionMeta | None = None) -> None:
        """Add an image with optional metadata."""
        self.images.append(image)
        self.metadata.append(meta or RegionMeta(index=len(self.images) - 1))

    def copy(self) -> 'ImageList':
        """Create a shallow copy of this ImageList."""
        return ImageList(
            images=list(self.images),
            metadata=list(self.metadata),
            source_width=self.source_width,
            source_height=self.source_height,
        )

    def with_images(self, new_images: list['Image']) -> 'ImageList':
        """Create a new ImageList with different images but same metadata.

        Used when filters process images - metadata is preserved.
        """
        if len(new_images) != len(self.images):
            raise ValueError(
                f"New images count ({len(new_images)}) must match "
                f"original count ({len(self.images)})"
            )
        return ImageList(
            images=new_images,
            metadata=self.metadata,  # Share metadata reference
            source_width=self.source_width,
            source_height=self.source_height,
        )

    def first(self) -> 'Image | None':
        """Get first image, or None if empty."""
        return self.images[0] if self.images else None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary (without image data)."""
        return {
            'count': len(self.images),
            'source_width': self.source_width,
            'source_height': self.source_height,
            'metadata': [
                {
                    'x': m.x, 'y': m.y,
                    'width': m.width, 'height': m.height,
                    'padding': m.padding,
                    'label': m.label,
                    'index': m.index,
                }
                for m in self.metadata
            ],
        }


__all__ = ['ImageList', 'RegionMeta']
