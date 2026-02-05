"""
StagForgeDocument - Pydantic model for SFR file I/O.

SFR Format: ZIP archive containing:
- content.json: Document structure (layers reference external files)
- layers/{id}.webp: Raster layer images (WebP for 8-bit)
- layers/{id}.svg: SVG layer content

Text layers are stored inline in content.json.
"""

import base64
import json
from pathlib import Path
from typing import Any, BinaryIO, ClassVar, Union

from pydantic import BaseModel, ConfigDict
from zipfile import ZipFile, ZIP_STORED

from stagforge.layers.document import Document


# Current SFR format version
VERSION = 2


class StagForgeDocument(BaseModel):
    """
    StagForge document format handler.

    This class wraps a Document and provides SFR file I/O operations.
    SFR files are ZIP archives containing document structure and layer assets.

    Example usage:
        # Load from file
        sfr_doc = StagForgeDocument.load('document.sfr')
        doc = sfr_doc.document

        # Save to file
        sfr_doc = StagForgeDocument(document=doc)
        sfr_doc.save('document.sfr')

        # Or use class method
        StagForgeDocument.save_document(doc, 'document.sfr')
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    # Current SFR format version
    VERSION: ClassVar[int] = VERSION

    # The wrapped document
    document: Document

    # --- Class Methods for Loading ---

    @classmethod
    def load(cls, file: Union[str, Path, BinaryIO]) -> 'StagForgeDocument':
        """
        Load a document from an SFR file.

        Args:
            file: Path to SFR file or file-like object

        Returns:
            StagForgeDocument instance with loaded document

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
            document = Document.from_api_dict(doc_data)

            return cls(document=document)

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

    # --- Instance Methods for Saving ---

    def save(self, file: Union[str, Path, BinaryIO]) -> None:
        """
        Save the document to an SFR file.

        Args:
            file: Path to SFR file or file-like object
        """
        self._save_document(self.document, file)

    @classmethod
    def save_document(cls, document: Document, file: Union[str, Path, BinaryIO]) -> None:
        """
        Save a document to an SFR file (class method alternative).

        Args:
            document: Document to save
            file: Path to SFR file or file-like object
        """
        cls._save_document(document, file)

    @classmethod
    def _save_document(cls, document: Document, file: Union[str, Path, BinaryIO]) -> None:
        """
        Internal method to save a document to an SFR file.

        Args:
            document: Document to save
            file: Path to SFR file or file-like object
        """
        with ZipFile(file, 'w', compression=ZIP_STORED) as zip_file:
            layers_for_json = []

            for layer in document.layers:
                layer_data = dict(layer)
                layer_type = layer.get('type', 'raster')
                layer_id = layer.get('id', 'unknown')

                # Handle SVG layers - extract content to separate file
                if layer_type == 'svg':
                    svg_content = layer_data.get('svgContent', '')
                    if svg_content:
                        filename = f'{layer_id}.svg'
                        zip_file.writestr(f'layers/{filename}', svg_content.encode('utf-8'))
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
            doc_dict = document.to_api_dict(include_content=True)
            # Remove layers from doc (they go in separate 'layers' key)
            doc_dict.pop('layers', None)

            content = {
                'format': 'stagforge',
                'version': cls.VERSION,
                'document': doc_dict,
                'layers': layers_for_json,
            }

            # Write content.json
            content_json = json.dumps(content, indent=2)
            zip_file.writestr('content.json', content_json)
