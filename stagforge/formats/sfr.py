"""
SFRDocument - Pydantic model for SFR documents and file I/O.

SFR Format: ZIP archive containing:
- content.json: Document structure (layers reference external files)
- layers/{id}.webp: Raster layer images (WebP for 8-bit)
- layers/{id}.svg: SVG layer content

Text layers are stored inline in content.json.

This is the single class for both document data model and SFR file operations.
"""

import base64
import json
import uuid
from pathlib import Path
from typing import Any, BinaryIO, ClassVar, Optional, Union
from zipfile import ZIP_STORED, ZipFile

from pydantic import BaseModel, ConfigDict, Field


# Current SFR format version
VERSION = 2


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


class SFRDocument(BaseModel):
    """
    StagForge document model with SFR file I/O support.

    This class represents a document with all its layers and metadata,
    and provides methods to load/save from SFR files.

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

    Example usage:
        # Load from file
        doc = SFRDocument.load('document.sfr')

        # Save to file
        doc.save('document.sfr')

        # Create new document
        doc = SFRDocument(name="My Document", width=800, height=600)
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=False,
        extra='ignore',
        arbitrary_types_allowed=True,
    )

    # Serialization version for document format
    DOC_VERSION: ClassVar[int] = 1
    # SFR file format version
    SFR_VERSION: ClassVar[int] = VERSION

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

    # Change tracking (for API polling optimization)
    change_counter: int = Field(default=0, alias='changeCounter')
    last_change_timestamp: float = Field(default=0, alias='lastChangeTimestamp')

    def model_post_init(self, __context: Any) -> None:
        """Set type_name to Document."""
        self.type_name = 'Document'

    # --- Document Data Methods ---

    def to_api_dict(self, *, include_content: bool = True) -> dict[str, Any]:
        """
        Convert to API response dictionary.

        Args:
            include_content: If False, excludes layer content (imageData, svgContent)

        Returns:
            Dict matching JS serialization format
        """
        self.version = self.DOC_VERSION
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

    def get_layer_objects(self) -> list:
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
            data['viewState'] = data.get(
                'viewState', {'zoom': 1.0, 'panX': 0, 'panY': 0}
            )
            data['foregroundColor'] = data.get('foregroundColor', '#000000')
            data['backgroundColor'] = data.get('backgroundColor', '#FFFFFF')
            data['_version'] = 1

        return data

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> 'SFRDocument':
        """
        Create SFRDocument from API/SFR dictionary.

        Args:
            data: Serialized document data

        Returns:
            SFRDocument instance
        """
        data = cls.migrate(data)
        return cls.model_validate(data)

    # --- SFR File I/O Methods ---

    @classmethod
    def load(cls, file: Union[str, Path, BinaryIO]) -> 'SFRDocument':
        """
        Load a document from an SFR file.

        Args:
            file: Path to SFR file or file-like object

        Returns:
            SFRDocument instance with loaded document

        Raises:
            ValueError: If file is not a valid SFR file
        """
        with ZipFile(file, 'r') as zip_file:
            # Read content.json
            try:
                content_text = zip_file.read('content.json').decode('utf-8')
            except KeyError:
                raise ValueError('Invalid SFR file: missing content.json')

            data = json.loads(content_text)

            # Validate format
            if data.get('format') != 'stagforge':
                raise ValueError('Invalid file format: not a Stagforge document')

            # Get document data
            doc_data = data.get('document', {})
            layers_data = data.get('layers', [])

            # Load layer content from ZIP
            for layer in layers_data:
                image_file = layer.get('imageFile')
                image_format = layer.get('imageFormat', 'webp')

                if image_file:
                    try:
                        file_data = zip_file.read(image_file)

                        if image_format == 'svg':
                            # SVG content is text
                            layer['svgContent'] = file_data.decode('utf-8')
                        else:
                            # Raster images become base64 data URLs
                            mime_type = f'image/{image_format}'
                            b64_data = base64.b64encode(file_data).decode('ascii')
                            layer['imageData'] = f'data:{mime_type};base64,{b64_data}'

                        # Remove file reference since we've loaded the content
                        del layer['imageFile']
                    except KeyError:
                        # File not found in ZIP, leave imageFile reference
                        pass

            # Build document data
            doc_data['layers'] = layers_data

            # Create document model
            return cls.from_api_dict(doc_data)

    @classmethod
    def load_metadata(cls, file: Union[str, Path, BinaryIO]) -> dict[str, Any]:
        """
        Load only the metadata from an SFR file (without layer content).

        Useful for getting document info without loading all image data.

        Args:
            file: Path to SFR file or file-like object

        Returns:
            Dict with document metadata
        """
        with ZipFile(file, 'r') as zip_file:
            try:
                content_text = zip_file.read('content.json').decode('utf-8')
            except KeyError:
                raise ValueError('Invalid SFR file: missing content.json')

            data = json.loads(content_text)

            if data.get('format') != 'stagforge':
                raise ValueError('Invalid file format: not a Stagforge document')

            # Return document metadata without layer content
            doc_data = data.get('document', {})
            layers_info = []

            for layer in data.get('layers', []):
                # Strip content, keep metadata
                layer_info = {
                    'id': layer.get('id'),
                    'name': layer.get('name'),
                    'type': layer.get('type'),
                    'width': layer.get('width'),
                    'height': layer.get('height'),
                    'visible': layer.get('visible', True),
                }
                layers_info.append(layer_info)

            return {
                'format_version': data.get('version', 1),
                'document': doc_data,
                'layer_count': len(layers_info),
                'layers': layers_info,
            }

    @classmethod
    def is_valid(cls, file: Union[str, Path, BinaryIO]) -> bool:
        """
        Check if a file is a valid SFR file.

        Args:
            file: Path to file or file-like object

        Returns:
            True if file is a valid SFR file
        """
        try:
            with ZipFile(file, 'r') as zip_file:
                if 'content.json' not in zip_file.namelist():
                    return False

                content_text = zip_file.read('content.json').decode('utf-8')
                data = json.loads(content_text)
                return data.get('format') == 'stagforge'
        except Exception:
            return False

    @classmethod
    def extract_thumbnail(cls, file: Union[str, Path, BinaryIO]) -> bytes | None:
        """
        Extract the thumbnail.jpg from an SFR file without loading the full document.

        Args:
            file: Path to SFR file or file-like object

        Returns:
            Thumbnail image bytes (JPEG) or None if not found
        """
        try:
            with ZipFile(file, 'r') as zip_file:
                if 'thumbnail.jpg' in zip_file.namelist():
                    return zip_file.read('thumbnail.jpg')
                return None
        except Exception:
            return None

    @classmethod
    def load_metadata_with_thumbnail(
        cls, file: Union[str, Path, BinaryIO]
    ) -> dict[str, Any]:
        """
        Load metadata and thumbnail from an SFR file.

        Similar to load_metadata() but also includes the thumbnail as base64.

        Args:
            file: Path to SFR file or file-like object

        Returns:
            Dict with document metadata and optional thumbnail_base64 field
        """
        metadata = cls.load_metadata(file)

        # Extract thumbnail
        thumbnail_bytes = cls.extract_thumbnail(file)
        if thumbnail_bytes:
            metadata['thumbnail_base64'] = base64.b64encode(thumbnail_bytes).decode(
                'ascii'
            )

        return metadata

    def save(self, file: Union[str, Path, BinaryIO]) -> None:
        """
        Save the document to an SFR file.

        Args:
            file: Path to SFR file or file-like object
        """
        with ZipFile(file, 'w', compression=ZIP_STORED) as zip_file:
            layers_for_json = []

            for layer in self.layers:
                layer_data = dict(layer)
                layer_type = layer.get('type', 'raster')
                layer_id = layer.get('id', 'unknown')

                # Handle SVG layers - extract content to separate file
                if layer_type == 'svg':
                    svg_content = layer_data.get('svgContent', '')
                    if svg_content:
                        filename = f'{layer_id}.svg'
                        zip_file.writestr(
                            f'layers/{filename}', svg_content.encode('utf-8')
                        )
                        layer_data['imageFile'] = f'layers/{filename}'
                        layer_data['imageFormat'] = 'svg'
                        # Remove inline content
                        layer_data.pop('svgContent', None)

                # Handle raster layers - extract image data to separate file
                elif layer_type == 'raster':
                    image_data = layer_data.get('imageData', '')
                    if image_data and image_data.startswith('data:'):
                        # Parse data URL: data:image/png;base64,<data>
                        try:
                            header, b64_data = image_data.split(',', 1)
                            mime_part = header.split(':')[1].split(';')[0]
                            image_format = mime_part.split('/')[1]

                            # Decode and save to ZIP
                            image_bytes = base64.b64decode(b64_data)
                            filename = f'{layer_id}.{image_format}'
                            zip_file.writestr(f'layers/{filename}', image_bytes)

                            layer_data['imageFile'] = f'layers/{filename}'
                            layer_data['imageFormat'] = image_format
                            # Remove inline content
                            layer_data.pop('imageData', None)
                        except (ValueError, IndexError):
                            # Failed to parse data URL, keep inline
                            pass

                layers_for_json.append(layer_data)

            # Build content.json
            doc_dict = self.to_api_dict(include_content=True)
            # Remove layers from doc (they go in separate 'layers' key)
            doc_dict.pop('layers', None)

            content = {
                'format': 'stagforge',
                'version': self.SFR_VERSION,
                'document': doc_dict,
                'layers': layers_for_json,
            }

            # Write content.json
            content_json = json.dumps(content, indent=2)
            zip_file.writestr('content.json', content_json)


# Backwards compatibility alias
Document = SFRDocument
