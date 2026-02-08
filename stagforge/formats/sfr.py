"""
SFRDocument - Pydantic model for SFR documents and file I/O.

SFR Format v3: ZIP archive containing:
- content.json: Document structure with pages (layers reference external files)
- layers/{id}.webp: Raster layer images (single-frame, WebP)
- layers/{id}_frame_{n}.webp: Raster layer frame images (multi-frame)
- layers/{id}.svg: SVG layer content (single-frame)
- layers/{id}_frame_{n}.svg: SVG layer frame content (multi-frame)

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
VERSION = 3


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

    This class represents a document with all its pages and metadata,
    and provides methods to load/save from SFR files.

    Serialization format (v2):
    {
        "_version": 2,
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
        "activePageIndex": 0,
        "pages": [
            {
                "id": "uuid",
                "name": "Page 1",
                "layers": [...],
                "activeLayerIndex": 0
            }
        ],
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
    DOC_VERSION: ClassVar[int] = 2
    # SFR file format version
    SFR_VERSION: ClassVar[int] = VERSION

    # Serialization metadata
    version: int = Field(default=2, alias='_version')
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

    # Pages (each page has its own layers)
    pages: list[dict[str, Any]] = Field(default_factory=list)
    active_page_index: int = Field(default=0, alias='activePageIndex')

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
        """Set type_name to Document and ensure at least one page exists."""
        self.type_name = 'Document'

        # Ensure at least one page exists
        if not self.pages:
            self.pages.append({
                'id': str(uuid.uuid4()),
                'name': 'Page 1',
                'layers': [],
                'activeLayerIndex': 0,
            })

    # --- Convenience accessors for active page layers ---

    @property
    def layers(self) -> list[dict[str, Any]]:
        """Get layers from the active page (convenience accessor)."""
        if self.pages and 0 <= self.active_page_index < len(self.pages):
            return self.pages[self.active_page_index].get('layers', [])
        return []

    @layers.setter
    def layers(self, value: list[dict[str, Any]]) -> None:
        """Set layers on the active page (convenience setter)."""
        if self.pages and 0 <= self.active_page_index < len(self.pages):
            self.pages[self.active_page_index]['layers'] = value

    @property
    def active_layer_index(self) -> int:
        """Get active layer index from the active page."""
        if self.pages and 0 <= self.active_page_index < len(self.pages):
            return self.pages[self.active_page_index].get('activeLayerIndex', 0)
        return 0

    def get_all_layers(self) -> list[dict[str, Any]]:
        """Get all layers across all pages."""
        all_layers = []
        for page in self.pages:
            all_layers.extend(page.get('layers', []))
        return all_layers

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
            # Remove large content from layers in all pages
            for page in data.get('pages', []):
                for layer in page.get('layers', []):
                    layer.pop('imageData', None)
                    layer.pop('svgContent', None)
                    layer.pop('_originalSvgContent', None)

        return data

    def get_layer(self, layer_id: str) -> Optional[dict[str, Any]]:
        """
        Get a layer by ID (searches all pages).

        Args:
            layer_id: Layer ID to find

        Returns:
            Layer dict or None if not found
        """
        for page in self.pages:
            for layer in page.get('layers', []):
                if layer.get('id') == layer_id:
                    return layer
        return None

    def get_layer_by_index(self, index: int) -> Optional[dict[str, Any]]:
        """
        Get a layer by index from the active page.

        Args:
            index: Layer index

        Returns:
            Layer dict or None if index out of range
        """
        layers = self.layers
        if 0 <= index < len(layers):
            return layers[index]
        return None

    def get_layer_objects(self) -> list:
        """
        Get all layers from active page as Pydantic model instances.

        Returns:
            List of layer model instances
        """
        from stagforge.layers import layer_from_dict

        return [layer_from_dict(layer) for layer in self.layers]

    def get_page_objects(self) -> list:
        """
        Get all pages as Page instances.

        Returns:
            List of Page instances
        """
        from stagforge.layers.page import Page

        return [Page.model_validate(page) for page in self.pages]

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

        # v1 -> v2: Migrate top-level layers to pages array
        if data.get('_version', 0) < 2:
            if 'layers' in data and 'pages' not in data:
                data['pages'] = [{
                    'id': str(uuid.uuid4()),
                    'name': 'Page 1',
                    'layers': data.pop('layers', []),
                    'activeLayerIndex': data.pop('activeLayerIndex', 0),
                }]
                data['activePageIndex'] = 0
            data['_version'] = 2

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
    def _load_layer_content(cls, layer: dict, zip_file: ZipFile) -> None:
        """Load a single layer's content from ZIP, handling multi-frame layers."""
        layer_type = layer.get('type', 'raster')

        # Handle multi-frame layers — frames array with file references
        frames = layer.get('frames', [])
        for frame in frames:
            image_file = frame.get('imageFile')
            image_format = frame.get('imageFormat', 'webp')

            if image_file:
                try:
                    file_data = zip_file.read(image_file)
                    if image_format == 'svg':
                        frame['svgContent'] = file_data.decode('utf-8')
                    else:
                        mime_type = f'image/{image_format}'
                        b64_data = base64.b64encode(file_data).decode('ascii')
                        frame['imageData'] = f'data:{mime_type};base64,{b64_data}'
                    del frame['imageFile']
                except KeyError:
                    pass

        # Handle single-frame layers (backward compat with v2 SFR files)
        image_file = layer.get('imageFile')
        image_format = layer.get('imageFormat', 'webp')

        if image_file:
            try:
                file_data = zip_file.read(image_file)

                if image_format == 'svg':
                    layer['svgContent'] = file_data.decode('utf-8')
                else:
                    mime_type = f'image/{image_format}'
                    b64_data = base64.b64encode(file_data).decode('ascii')
                    layer['imageData'] = f'data:{mime_type};base64,{b64_data}'

                del layer['imageFile']
            except KeyError:
                pass

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

            sfr_version = data.get('version', 1)
            doc_data = data.get('document', {})

            if sfr_version >= 3:
                # v3+: Pages are in content.json, layers per page
                pages_data = data.get('pages', [])
                for page in pages_data:
                    for layer in page.get('layers', []):
                        cls._load_layer_content(layer, zip_file)
                doc_data['pages'] = pages_data
            else:
                # v1-v2: Top-level layers array
                layers_data = data.get('layers', [])
                for layer in layers_data:
                    cls._load_layer_content(layer, zip_file)
                doc_data['layers'] = layers_data

            # Create document model (migrate will wrap layers into pages if needed)
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

            doc_data = data.get('document', {})
            sfr_version = data.get('version', 1)

            # Collect layer info from pages or top-level layers
            layers_info = []
            if sfr_version >= 3:
                pages_data = data.get('pages', [])
                for page in pages_data:
                    for layer in page.get('layers', []):
                        layers_info.append({
                            'id': layer.get('id'),
                            'name': layer.get('name'),
                            'type': layer.get('type'),
                            'width': layer.get('width'),
                            'height': layer.get('height'),
                            'visible': layer.get('visible', True),
                        })
            else:
                for layer in data.get('layers', []):
                    layers_info.append({
                        'id': layer.get('id'),
                        'name': layer.get('name'),
                        'type': layer.get('type'),
                        'width': layer.get('width'),
                        'height': layer.get('height'),
                        'visible': layer.get('visible', True),
                    })

            return {
                'format_version': sfr_version,
                'document': doc_data,
                'layer_count': len(layers_info),
                'layers': layers_info,
                'page_count': len(data.get('pages', [])) if sfr_version >= 3 else 1,
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

    @classmethod
    def _save_layer_content(
        cls, layer: dict, zip_file: ZipFile
    ) -> dict:
        """
        Save a single layer's content to ZIP, returning the layer dict for JSON.

        Handles both single-frame and multi-frame layers.
        Multi-frame layers store each frame as a separate file:
          layers/{layerId}_frame_{n}.webp / .svg
        Single-frame layers use the original naming:
          layers/{layerId}.webp / .svg
        """
        layer_data = dict(layer)
        layer_type = layer.get('type', 'raster')
        layer_id = layer.get('id', 'unknown')

        # Check if layer has multiple frames
        frames = layer_data.get('frames', [])
        is_multi_frame = len(frames) > 1

        if frames:
            # Save each frame's content to ZIP
            saved_frames = []
            for i, frame in enumerate(frames):
                frame_data = dict(frame)

                if is_multi_frame:
                    suffix = f'_frame_{i}'
                else:
                    suffix = ''

                if layer_type == 'svg':
                    svg_content = frame_data.get('svgContent', '')
                    if svg_content:
                        filename = f'{layer_id}{suffix}.svg'
                        zip_file.writestr(
                            f'layers/{filename}', svg_content.encode('utf-8')
                        )
                        frame_data['imageFile'] = f'layers/{filename}'
                        frame_data['imageFormat'] = 'svg'
                        frame_data.pop('svgContent', None)

                elif layer_type == 'raster':
                    image_data = frame_data.get('imageData', '')
                    if image_data and image_data.startswith('data:'):
                        try:
                            header, b64_data = image_data.split(',', 1)
                            mime_part = header.split(':')[1].split(';')[0]
                            image_format = mime_part.split('/')[1]

                            image_bytes = base64.b64decode(b64_data)
                            filename = f'{layer_id}{suffix}.{image_format}'
                            zip_file.writestr(f'layers/{filename}', image_bytes)

                            frame_data['imageFile'] = f'layers/{filename}'
                            frame_data['imageFormat'] = image_format
                            frame_data.pop('imageData', None)
                        except (ValueError, IndexError):
                            pass

                saved_frames.append(frame_data)

            layer_data['frames'] = saved_frames

        # Also handle top-level imageData/svgContent (backward compat for single-frame)
        if not frames:
            if layer_type == 'svg':
                svg_content = layer_data.get('svgContent', '')
                if svg_content:
                    filename = f'{layer_id}.svg'
                    zip_file.writestr(
                        f'layers/{filename}', svg_content.encode('utf-8')
                    )
                    layer_data['imageFile'] = f'layers/{filename}'
                    layer_data['imageFormat'] = 'svg'
                    layer_data.pop('svgContent', None)

            elif layer_type == 'raster':
                image_data = layer_data.get('imageData', '')
                if image_data and image_data.startswith('data:'):
                    try:
                        header, b64_data = image_data.split(',', 1)
                        mime_part = header.split(':')[1].split(';')[0]
                        image_format = mime_part.split('/')[1]

                        image_bytes = base64.b64decode(b64_data)
                        filename = f'{layer_id}.{image_format}'
                        zip_file.writestr(f'layers/{filename}', image_bytes)

                        layer_data['imageFile'] = f'layers/{filename}'
                        layer_data['imageFormat'] = image_format
                        layer_data.pop('imageData', None)
                    except (ValueError, IndexError):
                        pass

        return layer_data

    def save(self, file: Union[str, Path, BinaryIO]) -> None:
        """
        Save the document to an SFR file.

        Args:
            file: Path to SFR file or file-like object
        """
        with ZipFile(file, 'w', compression=ZIP_STORED) as zip_file:
            # Save pages with layer content extracted to ZIP
            pages_for_json = []
            for page in self.pages:
                page_data = dict(page)
                layers_for_json = []
                for layer in page_data.get('layers', []):
                    layers_for_json.append(
                        self._save_layer_content(layer, zip_file)
                    )
                page_data['layers'] = layers_for_json
                pages_for_json.append(page_data)

            # Build content.json
            doc_dict = self.to_api_dict(include_content=True)
            # Remove pages from doc (they go in separate 'pages' key)
            doc_dict.pop('pages', None)

            content = {
                'format': 'stagforge',
                'version': self.SFR_VERSION,
                'document': doc_dict,
                'pages': pages_for_json,
            }

            # Write content.json
            content_json = json.dumps(content, indent=2)
            zip_file.writestr('content.json', content_json)


# Backwards compatibility alias
Document = SFRDocument
