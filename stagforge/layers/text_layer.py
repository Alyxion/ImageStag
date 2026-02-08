"""
TextLayer - Layer with rich text rendered as SVG.

Text layers support multiple styled runs, each with:
- fontSize, fontFamily, fontWeight, fontStyle, color

The Python model is for serialization only. Text rendering happens in JS.
"""

from typing import Any, ClassVar, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .base import BaseLayer
from .frame import TextFrame
from .svg_base import SVGBaseLayer


class TextRun(BaseModel):
    """
    A single styled text run within a TextLayer.

    Text runs can override the layer's default typography settings.
    """
    text: str = Field(default='')
    font_size: Optional[int] = Field(default=None, alias='fontSize')
    font_family: Optional[str] = Field(default=None, alias='fontFamily')
    font_weight: Optional[str] = Field(default=None, alias='fontWeight')
    font_style: Optional[str] = Field(default=None, alias='fontStyle')
    color: Optional[str] = Field(default=None)

    # Text decorations
    underline: Optional[bool] = Field(default=None)
    strikethrough: Optional[bool] = Field(default=None)
    letter_spacing: Optional[float] = Field(default=None, alias='letterSpacing')

    model_config = {
        'populate_by_name': True,
    }


class TextLayer(SVGBaseLayer):
    """
    Text layer with rich text runs.

    Serialization format matches JS TextLayer.serialize():
    {
        "_version": 1,
        "_type": "TextLayer",
        "type": "text",
        "runs": [{"text": "Hello", "fontSize": 24}],
        "fontSize": 24,
        "fontFamily": "Arial",
        "fontWeight": "normal",
        "fontStyle": "normal",
        "textAlign": "left",
        "color": "#000000",
        "lineHeight": 1.2,
        "x": 0,
        "y": 0,
        ...base layer properties
    }
    """

    # Override version and layer_type
    VERSION: ClassVar[int] = 1
    layer_type: Literal["text"] = Field(default="text", alias="type")

    # Rich text runs
    runs: list[TextRun] = Field(default_factory=list)

    # Default typography settings
    font_size: int = Field(default=24, alias='fontSize')
    font_family: str = Field(default='Arial', alias='fontFamily')
    font_weight: str = Field(default='normal', alias='fontWeight')
    font_style: str = Field(default='normal', alias='fontStyle')
    text_align: str = Field(default='left', alias='textAlign')
    color: str = Field(default='#000000')
    line_height: float = Field(default=1.2, alias='lineHeight')

    # Position aliases (JS uses x/y as aliases for offsetX/offsetY)
    x: Optional[int] = Field(default=None)
    y: Optional[int] = Field(default=None)

    # Override frames with typed TextFrame list
    frames: list[TextFrame] = Field(default_factory=list)

    @field_validator('frames', mode='before')
    @classmethod
    def _coerce_text_frames(cls, v: Any) -> list:
        """Accept dicts and coerce them to TextFrame instances."""
        if not isinstance(v, list):
            return v
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(TextFrame.model_validate(item))
            else:
                result.append(item)
        return result

    def model_post_init(self, __context: Any) -> None:
        """Set type_name and sync position aliases."""
        self.type_name = 'TextLayer'

        # Sync x/y to offsetX/offsetY if provided
        if self.x is not None and self.offset_x == 0:
            self.offset_x = self.x
        if self.y is not None and self.offset_y == 0:
            self.offset_y = self.y

    def to_api_dict(self, *, include_content: bool = True) -> dict[str, Any]:
        """
        Convert to API response dictionary.

        Args:
            include_content: If False, excludes runs to reduce payload size

        Returns:
            Dict matching JS serialization format
        """
        self.version = self.VERSION

        # Sync position aliases
        self.x = self.offset_x
        self.y = self.offset_y

        data = self.model_dump(by_alias=True, mode='json')

        if not include_content:
            # Remove large content fields
            data.pop('runs', None)
            data.pop('_originalSvgContent', None)

        return data

    @property
    def text(self) -> str:
        """Get plain text content (all runs concatenated)."""
        return ''.join(run.text for run in self.runs)

    @text.setter
    def text(self, value: str) -> None:
        """Set plain text content (replaces all runs with single unstyled run)."""
        self.runs = [TextRun(text=value)]

    def has_content(self) -> bool:
        """Check if layer has text content."""
        return bool(self.text.strip())

    @classmethod
    def migrate(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate serialized data from older versions."""
        data = BaseLayer.migrate(data)

        # Handle pre-versioned data
        version = data.get('_version', 0)

        if version < 1:
            data['fontSize'] = data.get('fontSize', 24)
            data['fontFamily'] = data.get('fontFamily', 'Arial')
            data['fontWeight'] = data.get('fontWeight', 'normal')
            data['fontStyle'] = data.get('fontStyle', 'normal')
            data['textAlign'] = data.get('textAlign', 'left')
            data['color'] = data.get('color', '#000000')
            data['lineHeight'] = data.get('lineHeight', 1.2)
            data['_version'] = 1

        # Ensure transform state exists
        data['_contentRotation'] = data.get('_contentRotation', 0)
        data['_mirrorX'] = data.get('_mirrorX', False)
        data['_mirrorY'] = data.get('_mirrorY', False)

        return data

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> 'TextLayer':
        """Create TextLayer from API/SFR dictionary."""
        data = cls.migrate(data)
        return cls.model_validate(data)
