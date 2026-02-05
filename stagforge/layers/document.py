"""
Document - Represents a single document with all its state.

A document contains:
- Dimensions (width, height, DPI)
- Metadata (name, icon, color)
- Layers (as a flat list with parentId references)
- View state (zoom, pan)
- Colors (foreground, background)
- Saved selections

The Python model is for serialization only. Document editing happens in JS.
"""

from typing import Any, ClassVar, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseLayer


class ViewState(BaseModel):
    """Document view state (zoom and pan)."""
    zoom: float = Field(default=1.0)
    pan_x: float = Field(default=0, alias='panX')
    pan_y: float = Field(default=0, alias='panY')

    model_config = ConfigDict(populate_by_name=True)


class SavedSelection(BaseModel):
    """A saved selection (alpha mask with a name)."""
    name: str = Field(default='Selection')
    width: int = Field(default=0)
    height: int = Field(default=0)
    mask: str = Field(default='')  # Base64-encoded Uint8Array

    model_config = ConfigDict(populate_by_name=True)


class Document(BaseModel):
    """
    Document model matching JS Document.serialize().

    Serialization format:
    {
        "_version": 1,
        "_type": "Document",
        "id": "uuid",
        "name": "Untitled",
        "icon": "🎨",
        "color": "#E0E7FF",
        "width": 800,
        "height": 600,
        "dpi": 72,
        "foregroundColor": "#000000",
        "backgroundColor": "#FFFFFF",
        "layers": [...],
        "activeLayerIndex": 0,
        "viewState": {"zoom": 1.0, "panX": 0, "panY": 0},
        "savedSelections": []
    }
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=False,
        extra='ignore',
    )

    # Serialization version
    VERSION: ClassVar[int] = 1

    # Serialization metadata
    version: int = Field(default=1, alias='_version')
    type_name: str = Field(default='Document', alias='_type')

    # Identity
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default='Untitled')
    icon: str = Field(default='🎨')
    color: str = Field(default='#E0E7FF')

    # Dimensions
    width: int = Field(default=800, ge=1)
    height: int = Field(default=600, ge=1)
    dpi: int = Field(default=72, ge=1)

    # Colors
    foreground_color: str = Field(default='#000000', alias='foregroundColor')
    background_color: str = Field(default='#FFFFFF', alias='backgroundColor')

    # Layers (stored as dicts for serialization)
    layers: list[dict[str, Any]] = Field(default_factory=list)
    active_layer_index: int = Field(default=0, alias='activeLayerIndex')

    # View state
    view_state: ViewState = Field(default_factory=ViewState, alias='viewState')

    # Saved selections
    saved_selections: list[SavedSelection] = Field(
        default_factory=list, alias='savedSelections'
    )

    def model_post_init(self, __context: Any) -> None:
        """Set type_name to Document."""
        self.type_name = 'Document'

    def to_api_dict(self, *, include_content: bool = True) -> dict[str, Any]:
        """
        Convert to API response dictionary.

        Args:
            include_content: If False, excludes layer content (imageData, svgContent)

        Returns:
            Dict matching JS serialization format
        """
        self.version = self.VERSION
        data = self.model_dump(by_alias=True, mode='json')

        if not include_content:
            # Remove large content from layers
            for layer in data.get('layers', []):
                layer.pop('imageData', None)
                layer.pop('svgContent', None)
                layer.pop('_originalSvgContent', None)

        return data

    def get_layer(self, layer_id: str) -> Optional[dict[str, Any]]:
        """
        Get a layer by ID.

        Args:
            layer_id: Layer ID to find

        Returns:
            Layer dict or None if not found
        """
        for layer in self.layers:
            if layer.get('id') == layer_id:
                return layer
        return None

    def get_layer_by_index(self, index: int) -> Optional[dict[str, Any]]:
        """
        Get a layer by index.

        Args:
            index: Layer index

        Returns:
            Layer dict or None if index out of range
        """
        if 0 <= index < len(self.layers):
            return self.layers[index]
        return None

    def get_layer_objects(self) -> list[BaseLayer]:
        """
        Get all layers as Pydantic model instances.

        Returns:
            List of layer model instances
        """
        from stagforge.layers import layer_from_dict
        return [layer_from_dict(layer) for layer in self.layers]

    @classmethod
    def migrate(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Migrate serialized data from older versions.

        Args:
            data: Serialized document data

        Returns:
            Migrated data at current version
        """
        # Handle pre-versioned data
        version = data.get('_version', 0)

        # v0 -> v1: Ensure viewState, colors exist
        if version < 1:
            data['viewState'] = data.get('viewState', {
                'zoom': 1.0,
                'panX': 0,
                'panY': 0
            })
            data['foregroundColor'] = data.get('foregroundColor', '#000000')
            data['backgroundColor'] = data.get('backgroundColor', '#FFFFFF')
            data['_version'] = 1

        return data

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> 'Document':
        """
        Create Document from API/SFR dictionary.

        Args:
            data: Serialized document data

        Returns:
            Document instance
        """
        data = cls.migrate(data)
        return cls.model_validate(data)
