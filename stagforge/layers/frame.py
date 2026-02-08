"""
Frame classes for multi-frame layer support.

Each layer type has a corresponding frame type:
- Frame: Base class with id, duration (seconds), delay (seconds) (used by BaseLayer, LayerGroup)
- PixelFrame: Raster frame with image data (used by PixelLayer)
- SVGFrame: SVG content frame (used by StaticSVGLayer)
- TextFrame: Rich text runs frame (used by TextLayer)
"""

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Frame(BaseModel):
    """Base frame with id and duration."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra='ignore',
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    duration: float = Field(default=0.1)
    delay: float = Field(default=0.0)


class PixelFrame(Frame):
    """Raster frame with image data."""

    image_data: Optional[str] = Field(default=None, alias='imageData')
    image_file: Optional[str] = Field(default=None, alias='imageFile')
    image_format: str = Field(default='webp', alias='imageFormat')


class SVGFrame(Frame):
    """SVG content frame."""

    svg_content: str = Field(default='', alias='svgContent')


class TextFrame(Frame):
    """Rich text runs frame."""

    # Import TextRun at validation time to avoid circular imports.
    # Runs are stored as dicts during model construction and validated lazily.
    runs: list[dict] = Field(default_factory=list)
