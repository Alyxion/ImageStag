"""
LayerGroup - Container for organizing layers into folders.

Groups are non-renderable containers that:
- Organize layers hierarchically using flat array with parentId references
- Affect visibility and opacity of child layers
- Can be expanded/collapsed in the UI
- Do not have a canvas (not drawable)

The Python model is for serialization only. Group management happens in JS.
"""

from typing import Any, ClassVar, Literal

from pydantic import Field

from .base import BaseLayer, LayerType


class LayerGroup(BaseLayer):
    """
    Layer group for organizing layers.

    Serialization format matches JS LayerGroup.serialize():
    {
        "_version": 1,
        "_type": "LayerGroup",
        "type": "group",
        "expanded": true,
        "blendMode": "passthrough",
        ...base layer properties (width/height/offsetX/offsetY all 0)
    }
    """

    # Override version and layer_type
    VERSION: ClassVar[int] = 1
    layer_type: Literal["group"] = Field(default="group", alias="type")

    # UI state - whether group is expanded (showing children)
    expanded: bool = Field(default=True)

    # Groups default to passthrough blend mode
    blend_mode: str = Field(default='passthrough', alias='blendMode')

    # Groups have no dimensions (fixed at 0)
    width: int = Field(default=0)
    height: int = Field(default=0)
    offset_x: int = Field(default=0, alias='offsetX')
    offset_y: int = Field(default=0, alias='offsetY')

    # Groups don't have effects
    effects: list[dict[str, Any]] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        """Set type_name to LayerGroup and ensure group constraints."""
        self.type_name = 'LayerGroup'

        # Enforce group constraints
        self.width = 0
        self.height = 0
        self.offset_x = 0
        self.offset_y = 0
        self.effects = []

    def to_api_dict(self, *, include_content: bool = True) -> dict[str, Any]:
        """
        Convert to API response dictionary.

        Args:
            include_content: Ignored for groups (no content)

        Returns:
            Dict matching JS serialization format
        """
        self.version = self.VERSION
        return self.model_dump(by_alias=True, mode='json')

    def is_group(self) -> bool:
        """Check if this is a group layer."""
        return True

    def has_content(self) -> bool:
        """Groups have no content."""
        return False

    @classmethod
    def migrate(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate serialized data from older versions."""
        # Handle pre-versioned data
        version = data.get('_version', 0)

        # v0 -> v1: Ensure all fields exist
        if version < 1:
            data['parentId'] = data.get('parentId', None)
            data['expanded'] = data.get('expanded', True)
            data['blendMode'] = data.get('blendMode', 'passthrough')
            data['_version'] = 1

        return data

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> 'LayerGroup':
        """Create LayerGroup from API/SFR dictionary."""
        data = cls.migrate(data)
        return cls.model_validate(data)
