"""
PixelLayer - Raster layer with pixel data.

For SFR file I/O, pixel data can be stored as:
- `imageData`: Base64 data URL (inline in JSON, used for history/undo)
- `imageFile`: Path to image file in ZIP (used for SFR files)
- `imageFormat`: Format for external file ("webp" or "png")

The Python model is for serialization only. Canvas operations happen in JS.
"""

import base64
from io import BytesIO
from typing import Any, ClassVar, Literal, Optional

from pydantic import Field

from .base import BaseLayer, LayerType


class PixelLayer(BaseLayer):
    """
    Raster/pixel layer with image data.

    Serialization format matches JS PixelLayer.serialize():
    {
        "_version": 1,
        "_type": "PixelLayer",
        "type": "raster",
        "imageData": "data:image/png;base64,...",  // or
        "imageFile": "layers/abc123.webp",
        "imageFormat": "webp",
        ...base layer properties
    }
    """

    # Override version and layer_type
    VERSION: ClassVar[int] = 1
    layer_type: Literal["raster"] = Field(default="raster", alias="type")

    # Image data - either inline base64 or path to file in ZIP
    image_data: Optional[str] = Field(default=None, alias='imageData')
    image_file: Optional[str] = Field(default=None, alias='imageFile')
    image_format: str = Field(default='webp', alias='imageFormat')

    def model_post_init(self, __context: Any) -> None:
        """Set type_name to PixelLayer."""
        self.type_name = 'PixelLayer'

    def to_api_dict(self, *, include_content: bool = True) -> dict[str, Any]:
        """
        Convert to API response dictionary.

        Args:
            include_content: If False, excludes imageData to reduce payload size

        Returns:
            Dict matching JS serialization format
        """
        self.version = self.VERSION
        data = self.model_dump(by_alias=True, mode='json')

        if not include_content:
            # Remove large content fields
            data.pop('imageData', None)

        return data

    def get_image_bytes(self) -> Optional[bytes]:
        """
        Get raw image bytes from imageData.

        Returns:
            Image bytes or None if no imageData
        """
        if not self.image_data:
            return None

        # Parse data URL: data:image/png;base64,<data>
        if ',' in self.image_data:
            _, data = self.image_data.split(',', 1)
            return base64.b64decode(data)
        return None

    def set_image_bytes(self, data: bytes, format: str = 'png') -> None:
        """
        Set imageData from raw bytes.

        Args:
            data: Raw image bytes
            format: Image format (png, webp)
        """
        b64 = base64.b64encode(data).decode('ascii')
        self.image_data = f'data:image/{format};base64,{b64}'
        self.image_format = format

    def has_content(self) -> bool:
        """Check if layer has image content."""
        if self.width == 0 or self.height == 0:
            return False
        if self.image_data:
            # Check for empty data URL
            return self.image_data != 'data:image/png;base64,'
        if self.image_file:
            return True
        return False

    @classmethod
    def migrate(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate serialized data from older versions."""
        data = BaseLayer.migrate(data)

        # Ensure image fields exist
        if 'imageData' not in data and 'imageFile' not in data:
            data['imageData'] = 'data:image/png;base64,'

        return data

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> 'PixelLayer':
        """Create PixelLayer from API/SFR dictionary."""
        data = cls.migrate(data)
        return cls.model_validate(data)
