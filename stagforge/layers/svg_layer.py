"""
StaticSVGLayer - Layer with raw SVG content.

SVG layers store vector graphics as SVG strings. They support:
- Transform tracking for rotation/mirroring
- Natural dimensions from SVG viewBox
- Zoom-aware rendering (handled by JS)

The Python model is for serialization only. Rendering happens in JS/resvg.
"""

from typing import Any, ClassVar, Literal, Optional

from pydantic import Field, field_validator

from .base import BaseLayer
from .frame import SVGFrame
from .svg_base import SVGBaseLayer


class StaticSVGLayer(SVGBaseLayer):
    """
    SVG layer with vector content.

    Serialization format matches JS StaticSVGLayer.serialize():
    {
        "_version": 1,
        "_type": "StaticSVGLayer",
        "type": "svg",
        "svgContent": "<svg>...</svg>",
        "naturalWidth": 100,
        "naturalHeight": 100,
        "_originalSvgContent": "...",
        "_contentRotation": 0,
        ...base layer properties
    }
    """

    # Override version and layer_type
    VERSION: ClassVar[int] = 1
    layer_type: Literal["svg"] = Field(default="svg", alias="type")

    # SVG content
    svg_content: str = Field(default='', alias='svgContent')

    # Natural dimensions from SVG viewBox
    natural_width: float = Field(default=0, alias='naturalWidth')
    natural_height: float = Field(default=0, alias='naturalHeight')

    # Document dimensions for reference
    doc_width: Optional[int] = Field(default=None, alias='_docWidth')
    doc_height: Optional[int] = Field(default=None, alias='_docHeight')

    # Override frames with typed SVGFrame list
    frames: list[SVGFrame] = Field(default_factory=list)

    @field_validator('frames', mode='before')
    @classmethod
    def _coerce_svg_frames(cls, v: Any) -> list:
        """Accept dicts and coerce them to SVGFrame instances."""
        if not isinstance(v, list):
            return v
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(SVGFrame.model_validate(item))
            else:
                result.append(item)
        return result

    def model_post_init(self, __context: Any) -> None:
        """Set type_name to StaticSVGLayer."""
        self.type_name = 'StaticSVGLayer'

    def to_api_dict(self, *, include_content: bool = True) -> dict[str, Any]:
        """
        Convert to API response dictionary.

        Args:
            include_content: If False, excludes svgContent and _originalSvgContent

        Returns:
            Dict matching JS serialization format
        """
        self.version = self.VERSION
        data = self.model_dump(by_alias=True, mode='json')

        if not include_content:
            # Remove large content fields
            data.pop('svgContent', None)
            data.pop('_originalSvgContent', None)

        return data

    def has_content(self) -> bool:
        """Check if layer has SVG content."""
        return bool(self.svg_content)

    @classmethod
    def migrate(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate serialized data from older versions."""
        data = BaseLayer.migrate(data)

        # Handle pre-versioned data
        version = data.get('_version', 0)

        # v0 -> v1: Ensure all fields exist
        if version < 1:
            data['svgContent'] = data.get('svgContent', '')
            data['naturalWidth'] = data.get('naturalWidth', 0)
            data['naturalHeight'] = data.get('naturalHeight', 0)
            data['_docWidth'] = data.get('_docWidth', data.get('width', 0))
            data['_docHeight'] = data.get('_docHeight', data.get('height', 0))
            data['_version'] = 1

        # Ensure transform state exists
        data['_contentRotation'] = data.get('_contentRotation', 0)
        data['_mirrorX'] = data.get('_mirrorX', False)
        data['_mirrorY'] = data.get('_mirrorY', False)

        return data

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> 'StaticSVGLayer':
        """Create StaticSVGLayer from API/SFR dictionary."""
        data = cls.migrate(data)
        return cls.model_validate(data)


# Alias for backwards compatibility
SVGLayer = StaticSVGLayer
