"""
BaseLayer - Abstract base model for all layer types.

Provides shared properties for all layers:
- Identity: id, name, type, _version, _type
- Dimensions: width, height, offsetX, offsetY
- Transforms: rotation, scaleX, scaleY
- Appearance: opacity, blendMode, visible, locked
- Hierarchy: parentId
- Effects: effects[]

Uses Pydantic v2 with camelCase aliases for JS serialization compatibility.
"""

from enum import Enum
from typing import Any, ClassVar, Literal, Optional, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field

from imagestag.layer_effects.base import LayerEffect


class LayerType(str, Enum):
    """Layer type identifiers matching JS layer types."""
    RASTER = "raster"
    SVG = "svg"
    TEXT = "text"
    GROUP = "group"


class BaseLayer(BaseModel):
    """
    Base model for all layer types.

    Serializes to JSON format matching JS BaseLayer.getBaseSerializeData():
    {
        "_version": 1,
        "_type": "PixelLayer",
        "type": "raster",
        "id": "uuid",
        "name": "Layer 1",
        "width": 100,
        "height": 100,
        "offsetX": 0,
        "offsetY": 0,
        "rotation": 0,
        "scaleX": 1.0,
        "scaleY": 1.0,
        "opacity": 1.0,
        "blendMode": "normal",
        "visible": true,
        "locked": false,
        "parentId": null,
        "effects": []
    }
    """

    model_config = ConfigDict(
        # Allow both snake_case and camelCase input
        populate_by_name=True,
        # Use camelCase for JSON serialization
        alias_generator=None,  # We'll set aliases explicitly
        # Don't validate on assignment for performance
        validate_assignment=False,
        # Allow extra fields for forward compatibility
        extra='ignore',
        # Serialize enums by value (e.g., "raster" not "LayerType.RASTER")
        use_enum_values=True,
    )

    # Serialization version (matches JS BaseLayer.VERSION)
    VERSION: ClassVar[int] = 1

    # Serialization metadata (computed on dump)
    version: int = Field(default=1, alias='_version')
    type_name: str = Field(default='BaseLayer', alias='_type')

    # Layer type (overridden in subclasses with Literal types)
    # Serializes as "type" in JSON to match JS
    layer_type: str = Field(default="raster", alias="type")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default='Layer')

    # Dimensions (guard against NaN, clamp to max)
    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)

    # Offset from document origin (can be negative)
    offset_x: int = Field(default=0, alias='offsetX')
    offset_y: int = Field(default=0, alias='offsetY')

    # Transform properties (applied around layer center)
    rotation: float = Field(default=0.0)
    scale_x: float = Field(default=1.0, alias='scaleX')
    scale_y: float = Field(default=1.0, alias='scaleY')

    # Appearance
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    blend_mode: str = Field(default='normal', alias='blendMode')
    visible: bool = Field(default=True)
    locked: bool = Field(default=False)

    # Hierarchy (null = root level)
    parent_id: Optional[str] = Field(default=None, alias='parentId')

    # Layer effects (non-destructive)
    # Stored as dicts for serialization, converted to LayerEffect on load
    effects: list[dict[str, Any]] = Field(default_factory=list)

    # Multi-frame support
    frames: list[dict[str, Any]] = Field(default_factory=list)
    active_frame_index: int = Field(default=0, alias='activeFrameIndex')

    # Change tracking (for API polling optimization)
    change_counter: int = Field(default=0, alias='changeCounter')
    last_change_timestamp: float = Field(default=0, alias='lastChangeTimestamp')

    def model_post_init(self, __context: Any) -> None:
        """Set type_name to the actual class name."""
        self.type_name = self.__class__.__name__

    def to_api_dict(self, *, include_content: bool = True) -> dict[str, Any]:
        """
        Convert to API response dictionary.

        Uses camelCase keys for JS compatibility. Optionally excludes
        large content fields (imageData, svgContent) for metadata-only
        responses.

        Args:
            include_content: If False, excludes large binary/text data

        Returns:
            Dict matching JS serialization format
        """
        # Set version to class constant
        self.version = self.VERSION

        # Serialize with aliases (camelCase) and mode='json' for proper enum serialization
        data = self.model_dump(by_alias=True, mode='json')

        return data

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> 'BaseLayer':
        """
        Create layer from API/SFR dictionary.

        Accepts both camelCase (JS) and snake_case (Python) keys.

        Args:
            data: Dictionary from JS serialize() or Python to_api_dict()

        Returns:
            BaseLayer instance (or subclass based on type)
        """
        # Import here to avoid circular imports
        from stagforge.layers import get_layer_class

        # Determine layer type
        layer_type = data.get('type', 'raster')

        # Get appropriate class
        layer_class = get_layer_class(layer_type)

        # Pydantic handles alias resolution automatically
        return layer_class.model_validate(data)

    def add_effect(self, effect: Union[LayerEffect, dict[str, Any]]) -> None:
        """
        Add an effect to this layer.

        Args:
            effect: LayerEffect instance or serialized dict
        """
        if isinstance(effect, LayerEffect):
            self.effects.append(effect.to_dict())
        else:
            self.effects.append(effect)

    def remove_effect(self, effect_id: str) -> bool:
        """
        Remove an effect by ID.

        Args:
            effect_id: Effect ID to remove

        Returns:
            True if effect was found and removed
        """
        for i, effect in enumerate(self.effects):
            if effect.get('id') == effect_id:
                self.effects.pop(i)
                return True
        return False

    def get_effect(self, effect_id: str) -> Optional[dict[str, Any]]:
        """
        Get an effect by ID.

        Args:
            effect_id: Effect ID to find

        Returns:
            Effect dict or None if not found
        """
        for effect in self.effects:
            if effect.get('id') == effect_id:
                return effect
        return None

    def get_effect_objects(self) -> list[LayerEffect]:
        """
        Get all effects as LayerEffect instances.

        Returns:
            List of LayerEffect instances
        """
        result = []
        for effect_data in self.effects:
            try:
                effect = LayerEffect.from_dict(effect_data)
                result.append(effect)
            except (ValueError, KeyError):
                # Skip invalid effects
                pass
        return result

    def has_transform(self) -> bool:
        """Check if this layer has any transform (rotation or non-unit scale)."""
        return self.rotation != 0 or self.scale_x != 1.0 or self.scale_y != 1.0

    def get_bounds(self) -> dict[str, int]:
        """
        Get the bounds of this layer in document coordinates.

        Returns:
            Dict with x, y, width, height
        """
        return {
            'x': self.offset_x,
            'y': self.offset_y,
            'width': self.width,
            'height': self.height,
        }

    def is_group(self) -> bool:
        """Check if this is a group layer."""
        return self.layer_type == "group"

    def is_raster(self) -> bool:
        """Check if this is a raster/pixel layer."""
        return self.layer_type == "raster"

    def is_text(self) -> bool:
        """Check if this is a text layer."""
        return self.layer_type == "text"

    def is_svg(self) -> bool:
        """Check if this is an SVG layer."""
        return self.layer_type == "svg"

    @classmethod
    def migrate(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Migrate serialized data from older versions.

        Args:
            data: Serialized layer data

        Returns:
            Migrated data at current version
        """
        # Handle pre-versioned data
        version = data.get('_version', 0)

        # v0 -> v1: Ensure offsetX/offsetY and parentId exist
        if version < 1:
            data['offsetX'] = data.get('offsetX', 0)
            data['offsetY'] = data.get('offsetY', 0)
            data['parentId'] = data.get('parentId', None)
            data['_version'] = 1

        # Ensure transform properties exist
        data['rotation'] = data.get('rotation', 0)
        data['scaleX'] = data.get('scaleX', 1.0)
        data['scaleY'] = data.get('scaleY', 1.0)

        return data
